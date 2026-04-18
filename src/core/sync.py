"""Nemo Tracker — Синхронизация с Marzban API."""

from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.marzban_client import marzban_client
from src.models.database import User, Connection
from src.models import async_session


# Порог: считаем юзера онлайн если online_at в пределах последних 2 минут
_ONLINE_THRESHOLD_SEC = 120


def _parse_dt(value: Any) -> datetime | None:
    """Парсит дату из Marzban ответа (unix timestamp, ISO строка, datetime)."""
    if not value:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    try:
        from dateutil.parser import parse as dt_parse
        return dt_parse(str(value))
    except Exception:
        return None


def _is_online(online_at: datetime | None) -> bool:
    if not online_at:
        return False
    now = datetime.now(timezone.utc)
    if online_at.tzinfo is None:
        online_at = online_at.replace(tzinfo=timezone.utc)
    return (now - online_at).total_seconds() < _ONLINE_THRESHOLD_SEC


async def sync_all_users() -> Tuple[int, int, List[str]]:
    """Забрать всех юзеров из Marzban, обновить кэш.
    
    Returns: (total, new_count, new_usernames)
    """
    all_users_data: List[Dict] = []
    offset = 0
    limit = 100
    
    while True:
        batch = await marzban_client.get_all_users(offset=offset, limit=limit)
        if not batch:
            break
        all_users_data.extend(batch)
        if len(batch) < limit:
            break
        offset += limit

    new_usernames: List[str] = []
    
    async with async_session() as session:
        for udata in all_users_data:
            username = udata.get("username")
            if not username:
                continue
            
            online_at = _parse_dt(udata.get("online_at"))
            expire = _parse_dt(udata.get("expire"))
            used_traffic = udata.get("used_traffic", 0) or 0
            data_limit = udata.get("data_limit")
            status = udata.get("status", "active")
            
            # Определяем лимит в GB
            gb_limit = None
            if data_limit and data_limit > 0:
                gb_limit = round(data_limit / (1024**3), 2)

            # Определяем tier по inbounds
            inbounds = udata.get("inbounds") or {}
            all_tags = [tag for tags in inbounds.values() for tag in tags]
            tier = 1 if "vless-reality-whitelist" in all_tags else 0

            # Лимит устройств из Marzban
            ip_limit = udata.get("ip_limit") or 0

            # Проверяем есть ли юзер в кэше
            result = await session.execute(select(User).where(User.username == username))
            db_user = result.scalar_one_or_none()

            if db_user is None:
                db_user = User(
                    username=username,
                    status=status,
                    used_traffic=used_traffic,
                    data_limit=data_limit,
                    online_at=online_at,
                    expire=expire,
                    gb_limit=gb_limit,
                    tier=tier,
                    device_count=ip_limit,
                    was_online=_is_online(online_at),
                    last_synced=datetime.now(timezone.utc),
                )
                session.add(db_user)
                new_usernames.append(username)
            else:
                db_user.status = status
                db_user.used_traffic = used_traffic
                db_user.data_limit = data_limit
                db_user.online_at = online_at
                db_user.expire = expire
                db_user.gb_limit = gb_limit
                db_user.tier = tier
                db_user.device_count = ip_limit
                db_user.last_synced = datetime.now(timezone.utc)

        await session.commit()

    logger.info(f"Synced {len(all_users_data)} users, {len(new_usernames)} new")
    return len(all_users_data), len(new_usernames), new_usernames


async def sync_system_stats() -> Dict[str, Any]:
    """Забрать системную статистику Marzban."""
    try:
        stats = await marzban_client.get_system_stats()
        logger.debug(f"System stats: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        return {}


async def detect_changes() -> Tuple[List[str], List[str]]:
    """Сравнить текущее состояние с предыдущим, найти новые подключения/отключения.
    
    Returns: (went_online, went_offline) — списки username
    """
    went_online: List[str] = []
    went_offline: List[str] = []

    # Забираем свежие данные из Marzban
    all_users_data: List[Dict] = []
    offset = 0
    while True:
        batch = await marzban_client.get_all_users(offset=offset, limit=100)
        if not batch:
            break
        all_users_data.extend(batch)
        if len(batch) < 100:
            break
        offset += 100

    async with async_session() as session:
        for udata in all_users_data:
            username = udata.get("username")
            if not username:
                continue

            result = await session.execute(select(User).where(User.username == username))
            db_user = result.scalar_one_or_none()
            if db_user is None:
                continue  # Будет обработан при sync_all_users

            online_at = _parse_dt(udata.get("online_at"))
            now_online = _is_online(online_at)
            was_online = db_user.was_online

            if now_online and not was_online:
                # Пользователь подключился
                went_online.append(username)
                db_user.was_online = True
                db_user.online_at = online_at
                # Создаём запись о подключении
                conn = Connection(
                    username=username,
                    online_at=online_at or datetime.now(timezone.utc),
                    node_name="Standard-VPN",
                )
                session.add(conn)

            elif not now_online and was_online:
                # Пользователь отключился
                went_offline.append(username)
                db_user.was_online = False
                # Закрываем последнюю открытую запись подключения
                open_conn = await session.execute(
                    select(Connection)
                    .where(Connection.username == username, Connection.offline_at.is_(None))
                    .order_by(Connection.id.desc())
                    .limit(1)
                )
                conn = open_conn.scalar_one_or_none()
                if conn:
                    conn.offline_at = datetime.now(timezone.utc)
                    if conn.online_at:
                        dur = (conn.offline_at - conn.online_at).total_seconds() / 60
                        conn.duration_min = round(dur, 1)

        await session.commit()

    if went_online or went_offline:
        logger.info(f"Changes: +{len(went_online)} online, -{len(went_offline)} offline")
    
    return went_online, went_offline
