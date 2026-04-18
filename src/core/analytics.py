"""Nemo Tracker — Аналитика."""

from datetime import datetime, timedelta, date, timezone
from typing import List, Dict, Any, Optional

from loguru import logger
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import User, Connection, Analytics
from src.models import async_session


async def calculate_daily_stats(target_date: Optional[date] = None) -> Optional[Analytics]:
    """Агрегация статистики за день. Если date=None — за сегодня."""
    if target_date is None:
        target_date = date.today()

    async with async_session() as session:
        # Total users
        total_users = await session.scalar(select(func.count(User.id)))

        # Active users (status = active)
        active_users = await session.scalar(
            select(func.count(User.id)).where(User.status == "active")
        )

        # Users who were online today
        day_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)

        online_users = await session.scalar(
            select(func.count(func.distinct(Connection.username))).where(
                Connection.online_at >= day_start,
                Connection.online_at < day_end,
            )
        ) or 0

        # Total traffic (used_traffic sum in GB)
        total_traffic_bytes = await session.scalar(
            select(func.coalesce(func.sum(User.used_traffic), 0))
        )
        total_traffic_gb = round(total_traffic_bytes / (1024**3), 2)

        # New users (created today)
        new_users = await session.scalar(
            select(func.count(User.id)).where(
                User.created_at >= day_start,
                User.created_at < day_end,
            )
        ) or 0

        # Expired users
        expired_users = await session.scalar(
            select(func.count(User.id)).where(
                User.status == "expired",
            )
        ) or 0

        # Upsert analytics row
        result = await session.execute(
            select(Analytics).where(Analytics.date == target_date)
        )
        row = result.scalar_one_or_none()

        if row is None:
            row = Analytics(date=target_date)
            session.add(row)

        row.total_users = total_users
        row.active_users = active_users
        row.online_users = online_users
        row.total_traffic_gb = total_traffic_gb
        row.new_users = new_users
        row.expired_users = expired_users

        await session.commit()
        logger.info(f"Analytics for {target_date}: {total_users} total, {online_users} online, {total_traffic_gb} GB")
        return row


async def get_traffic_trends(days: int = 30) -> List[Dict[str, Any]]:
    """Тренд трафика за N дней."""
    async with async_session() as session:
        result = await session.execute(
            select(Analytics)
            .where(Analytics.date >= date.today() - timedelta(days=days))
            .order_by(Analytics.date)
        )
        rows = result.scalars().all()
        return [
            {"date": str(r.date), "traffic_gb": r.total_traffic_gb, "online": r.online_users}
            for r in rows
        ]


async def get_online_timeline(hours: int = 24) -> List[Dict[str, Any]]:
    """Кто был онлайн за последние N часов."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    async with async_session() as session:
        result = await session.execute(
            select(Connection.username, Connection.online_at, Connection.offline_at)
            .where(Connection.online_at >= since)
            .order_by(Connection.online_at.desc())
        )
        rows = result.all()
        return [
            {"username": r[0], "online_at": str(r[1]), "offline_at": str(r[2]) if r[2] else None}
            for r in rows
        ]


async def get_user_growth(days: int = 30) -> List[Dict[str, Any]]:
    """Рост пользовательской базы за N дней."""
    async with async_session() as session:
        result = await session.execute(
            select(Analytics.date, Analytics.total_users, Analytics.new_users)
            .where(Analytics.date >= date.today() - timedelta(days=days))
            .order_by(Analytics.date)
        )
        rows = result.all()
        return [{"date": str(r[0]), "total": r[1], "new": r[2]} for r in rows]


async def get_peak_hours() -> List[Dict[str, Any]]:
    """Пиковые часы по подключениям (топ-10 часов)."""
    async with async_session() as session:
        # Считаем подключения по часам за последние 7 дней
        result = await session.execute(
            select(
                func.extract("hour", Connection.online_at).label("hour"),
                func.count().label("cnt"),
            )
            .where(Connection.online_at >= datetime.now(timezone.utc) - timedelta(days=7))
            .group_by("hour")
            .order_by(func.count().desc())
            .limit(10)
        )
        rows = result.all()
        return [{"hour": int(r[0]), "connections": r[1]} for r in rows]


async def get_retention(days: int = 30) -> Dict[str, Any]:
    """Удержание: % юзеров кто был онлайн хотя бы раз за N дней."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    async with async_session() as session:
        total = await session.scalar(select(func.count(User.id))) or 1
        active_in_period = await session.scalar(
            select(func.count(func.distinct(Connection.username))).where(
                Connection.online_at >= since
            )
        ) or 0
        retention_pct = round((active_in_period / total) * 100, 1)
        return {
            "period_days": days,
            "total_users": total,
            "active_in_period": active_in_period,
            "retention_pct": retention_pct,
        }
