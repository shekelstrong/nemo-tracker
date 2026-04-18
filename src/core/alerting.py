"""Nemo Tracker — Система уведомлений."""

from datetime import datetime, timedelta, timezone, date
from typing import List, Dict, Any

from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import User, Alert
from src.models import async_session


async def check_new_users(new_usernames: List[str]) -> List[Alert]:
    """Создать алерт на каждого нового пользователя."""
    alerts: List[Alert] = []
    if not new_usernames:
        return alerts

    async with async_session() as session:
        for username in new_usernames:
            alert = Alert(
                username=username,
                alert_type="new_user",
                message=f"🆕 Новый пользователь: {username}",
            )
            session.add(alert)
            alerts.append(alert)
        await session.commit()

    logger.info(f"Created {len(alerts)} new_user alerts")
    return alerts


async def check_online_status(went_online: List[str], went_offline: List[str]) -> List[Alert]:
    """Лог подключений/отключений как алерты."""
    alerts: List[Alert] = []

    async with async_session() as session:
        for username in went_online:
            alert = Alert(
                username=username,
                alert_type="online",
                message=f"🟢 {username} подключился",
            )
            session.add(alert)
            alerts.append(alert)

        for username in went_offline:
            alert = Alert(
                username=username,
                alert_type="offline",
                message=f"🔴 {username} отключился",
            )
            session.add(alert)
            alerts.append(alert)

        await session.commit()

    return alerts


async def check_traffic_limits() -> List[Alert]:
    """Проверить: трафик превысил 80% лимита."""
    alerts: List[Alert] = []

    async with async_session() as session:
        # Юзеры у которых data_limit задан и used_traffic > 80%
        result = await session.execute(
            select(User).where(
                User.data_limit.isnot(None),
                User.data_limit > 0,
                User.status == "active",
            )
        )
        users = result.scalars().all()

        for user in users:
            pct = user.traffic_usage_percent()
            if pct is None or pct < 80:
                continue

            # Проверяем нет ли уже активного алерта
            existing = await session.scalar(
                select(func.count()).select_from(Alert).where(
                    Alert.username == user.username,
                    Alert.alert_type == "traffic_80",
                    Alert.resolved == False,
                )
            ) if False else 0  # inline import avoided; check below

            from sqlalchemy import func as sqlfunc
            existing = await session.scalar(
                select(sqlfunc.count()).select_from(Alert).where(
                    Alert.username == user.username,
                    Alert.alert_type == "traffic_80",
                    Alert.resolved == False,
                )
            )

            if existing and existing > 0:
                continue

            pct_str = f"{pct:.1f}"
            used_gb = round(user.used_traffic / (1024**3), 2)
            limit_gb = round(user.data_limit / (1024**3), 2)
            alert = Alert(
                username=user.username,
                alert_type="traffic_80",
                message=f"⚠️ {user.username}: трафик {pct_str}% ({used_gb}/{limit_gb} GB)",
            )
            session.add(alert)
            alerts.append(alert)

        await session.commit()

    logger.info(f"Traffic alerts: {len(alerts)}")
    return alerts


async def check_expiring_users(days_before: int = 3) -> List[Alert]:
    """Подписка истекает через N дней → напоминание."""
    alerts: List[Alert] = []
    threshold = datetime.now(timezone.utc) + timedelta(days=days_before)

    async with async_session() as session:
        result = await session.execute(
            select(User).where(
                User.expire.isnot(None),
                User.expire <= threshold,
                User.expire > datetime.now(timezone.utc),
                User.status == "active",
            )
        )
        users = result.scalars().all()

        for user in users:
            from sqlalchemy import func as sqlfunc
            # Проверяем нет ли алерта за сегодня
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            existing = await session.scalar(
                select(sqlfunc.count()).select_from(Alert).where(
                    Alert.username == user.username,
                    Alert.alert_type == "expiring_3d",
                    Alert.created_at >= today_start,
                )
            )
            if existing and existing > 0:
                continue

            days_left = (user.expire - datetime.now(timezone.utc)).days
            alert = Alert(
                username=user.username,
                alert_type="expiring_3d",
                message=f"⏰ {user.username}: подписка истекает через {days_left} дн.",
            )
            session.add(alert)
            alerts.append(alert)

        await session.commit()

    logger.info(f"Expiring alerts: {len(alerts)}")
    return alerts


async def get_unresolved_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    """Получить неразрешённые алерты."""
    async with async_session() as session:
        result = await session.execute(
            select(Alert)
            .where(Alert.resolved == False)
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )
        alerts = result.scalars().all()
        return [
            {
                "id": a.id,
                "username": a.username,
                "type": a.alert_type,
                "message": a.message,
                "created_at": str(a.created_at),
            }
            for a in alerts
        ]


async def resolve_alert(alert_id: int) -> bool:
    """Пометить алерт как разрешённый."""
    async with async_session() as session:
        result = await session.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one_or_none()
        if alert:
            alert.resolved = True
            await session.commit()
            return True
    return False
