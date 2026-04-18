"""Auto-renewal system for Nemo Tracker subscriptions.

Handles periodic subscription renewal checks, payment stubs,
Marzban API integration, and Telegram notifications.
"""

from datetime import datetime, timedelta
from typing import Optional

from loguru import logger
from sqlalchemy import select, func

from src.models import async_session
from src.models.database import AutoRenewal, TariffPlan, User as DBUser, Transaction
from src.core.marzban_client import marzban_client
from src.config import settings


async def check_renewals():
    """Check and process subscriptions due for renewal (called every 6 hours).

    Finds subscriptions with next_renewal_at < now + 24h.
    For each: attempts payment (stub), extends in Marzban, updates timestamps.
    On failure: increments fail_count, disables after 3 failures.
    """
    now = datetime.utcnow()
    threshold = now + timedelta(hours=24)

    async with async_session() as session:
        rows = (await session.execute(
            select(AutoRenewal).where(
                AutoRenewal.is_active == True,
                AutoRenewal.next_renewal_at != None,
                AutoRenewal.next_renewal_at < threshold,
            )
        )).scalars().all()

        if not rows:
            return

        logger.info(f"[AutoRenewal] Processing {len(rows)} renewals")

        for ar in rows:
            try:
                await _process_renewal(session, ar, now)
            except Exception as e:
                logger.error(f"[AutoRenewal] Error renewing {ar.username}: {e}")
                ar.fail_count += 1
                if ar.fail_count >= 3:
                    ar.is_active = False
                    logger.warning(f"[AutoRenewal] Disabled auto-renewal for {ar.username} after 3 failures")
                    await _send_telegram(
                        ar.telegram_id,
                        _t(ar.telegram_id,
                           f"❌ Auto-renewal disabled for {ar.username} after 3 failed attempts. "
                           f"Please update your payment method.",
                           f"❌ Автопродление для {ar.username} отключено после 3 неудачных попыток. "
                           f"Обновите способ оплаты.")
                    )

        await session.commit()


async def send_reminder():
    """Send Telegram reminders for subscriptions expiring within 3 days.

    Only notifies users who do NOT have auto-renewal enabled.
    """
    now = datetime.utcnow()
    threshold = now + timedelta(days=3)

    async with async_session() as session:
        # Find users expiring soon
        users = (await session.execute(
            select(DBUser).where(
                DBUser.expire != None,
                DBUser.expire < threshold,
                DBUser.expire > now,
                DBUser.status == "active",
            )
        )).scalars().all()

        # Get usernames with active auto-renewal
        ar_users = set((await session.execute(
            select(AutoRenewal.username).where(AutoRenewal.is_active == True)
        )).scalars().all())

        for user in users:
            if user.username in ar_users:
                continue  # already has auto-renewal
            if not hasattr(user, 'telegram_id') or not user.telegram_id:
                continue

            days_left = (user.expire - now).days
            await _send_telegram(
                user.telegram_id,
                _t(user.telegram_id,
                   f"⏰ Your subscription expires in {days_left} day(s). Enable auto-renewal to avoid interruption!",
                   f"⏰ Ваша подписка истекает через {days_left} дн. Включите автопродление, чтобы не остаться без VPN!")
            )

        logger.info(f"[AutoRenewal] Sent reminders to {len(users)} users")


async def _process_renewal(session, ar: AutoRenewal, now: datetime):
    """Process a single renewal: charge (stub), extend, update."""
    # Get tariff
    tariff = None
    if ar.tariff_id:
        tariff = (await session.execute(
            select(TariffPlan).where(TariffPlan.id == ar.tariff_id)
        )).scalar_one_or_none()

    # --- Payment stub ---
    amount = tariff.price_rub if tariff else 0
    currency = "RUB"
    logger.info(
        f"[AutoRenewal] STUB: would charge {amount} {currency} from {ar.username} "
        f"via {ar.payment_method}"
    )

    # Simulate payment success (stub)
    payment_ok = True

    if not payment_ok:
        ar.fail_count += 1
        logger.warning(f"[AutoRenewal] Payment failed for {ar.username} (fail #{ar.fail_count})")
        if ar.fail_count >= 3:
            ar.is_active = False
            await _send_telegram(
                ar.telegram_id,
                _t(ar.telegram_id,
                   f"❌ Auto-renewal payment failed for {ar.username}. Auto-renewal disabled.",
                   f"❌ Оплата автопродления для {ar.username} не прошла. Автопродление отключено.")
            )
        return

    # --- Extend in Marzban ---
    duration_days = tariff.duration_days if tariff else 30
    db_user = (await session.execute(
        select(DBUser).where(DBUser.username == ar.username)
    )).scalar_one_or_none()

    current_expire = db_user.expire if db_user and db_user.expire else now
    if current_expire < now:
        current_expire = now
    new_expire_ts = int((current_expire + timedelta(days=duration_days)).timestamp())

    await marzban_client.update_user(ar.username, expire=new_expire_ts)

    # Update device limit from tariff if set
    if tariff and tariff.device_limit:
        from src.core.device_tracker import device_tracker
        await device_tracker.set_device_limit(ar.username, tariff.device_limit)

    # --- Record transaction ---
    tx = Transaction(
        username=ar.username,
        user_telegram_id=ar.telegram_id,
        amount=amount,
        currency=currency,
        payment_method=ar.payment_method,
        status="paid",
        description="Auto-renewal",
    )
    session.add(tx)

    # --- Update auto-renewal record ---
    ar.last_renewed_at = now
    ar.next_renewal_at = current_expire + timedelta(days=duration_days)
    ar.fail_count = 0

    logger.info(f"[AutoRenewal] Renewed {ar.username} for {duration_days} days")

    await _send_telegram(
        ar.telegram_id,
        _t(ar.telegram_id,
           f"✅ Subscription renewed for {duration_days} days. Next renewal: {ar.next_renewal_at.strftime('%d.%m.%Y')}",
           f"✅ Подписка продлена на {duration_days} дней. Следующее продление: {ar.next_renewal_at.strftime('%d.%m.%Y')}")
    )


async def _send_telegram(telegram_id: Optional[int], text: str):
    """Send Telegram notification via bot."""
    if not telegram_id or not settings.bot_token:
        return
    try:
        import aiohttp
        async with aiohttp.ClientSession() as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
                json={"chat_id": telegram_id, "text": text, "parse_mode": "HTML"},
            )
    except Exception as e:
        logger.error(f"[AutoRenewal] Telegram send error: {e}")


def _t(telegram_id: Optional[int], en: str, ru: str) -> str:
    """Simple bilingual text selector. Default to RU."""
    # Could be extended with user language preference
    return ru
