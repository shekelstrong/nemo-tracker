"""Multi-server manager for Marzban nodes."""

import asyncio
from datetime import datetime
from typing import Optional

import aiohttp
from cryptography.fernet import Fernet
from loguru import logger
from sqlalchemy import select, desc

from src.config import settings
from src.models import async_session
from src.models.database import Server


def _get_fernet() -> Fernet:
    """Get Fernet instance from config key (padded/encoded to 32 bytes)."""
    import base64
    key = settings.server_encrypt_key.encode()
    # Ensure 32 bytes for Fernet
    key = base64.urlsafe_b64encode(key.ljust(32, b'\0')[:32])
    return Fernet(key)


def encrypt_password(password: str) -> str:
    return _get_fernet().encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()


async def add_server(
    name: str,
    url: str,
    username: str,
    password: str,
    country: Optional[str] = None,
    city: Optional[str] = None,
    ip_address: Optional[str] = None,
    max_users: Optional[int] = None,
    is_master: bool = False,
) -> Server:
    async with async_session() as session:
        enc_pass = encrypt_password(password)
        srv = Server(
            name=name,
            marzban_url=url.rstrip("/"),
            marzban_username=username,
            marzban_password=enc_pass,
            country=country,
            city=city,
            ip_address=ip_address,
            max_users=max_users,
            is_master=is_master,
            status="offline",
        )
        session.add(srv)
        await session.commit()
        await session.refresh(srv)
        return srv


async def remove_server(server_id: int) -> bool:
    async with async_session() as session:
        srv = (await session.execute(
            select(Server).where(Server.id == server_id)
        )).scalar_one_or_none()
        if not srv:
            return False
        await session.delete(srv)
        await session.commit()
        return True


async def update_server(server_id: int, **kwargs) -> Optional[Server]:
    async with async_session() as session:
        srv = (await session.execute(
            select(Server).where(Server.id == server_id)
        )).scalar_one_or_none()
        if not srv:
            return None
        for key, val in kwargs.items():
            if key == "marzban_password" and val:
                val = encrypt_password(val)
            if hasattr(srv, key):
                setattr(srv, key, val)
        await session.commit()
        await session.refresh(srv)
        return srv


async def get_all_servers() -> list[Server]:
    async with async_session() as session:
        rows = (await session.execute(
            select(Server).order_by(desc(Server.is_master), Server.name)
        )).scalars().all()
        return list(rows)


async def get_server(server_id: int) -> Optional[Server]:
    async with async_session() as session:
        return (await session.execute(
            select(Server).where(Server.id == server_id)
        )).scalar_one_or_none()


async def _marzban_login(url: str, username: str, password: str) -> Optional[str]:
    """Authenticate with Marzban and return token."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as sess:
            resp = await sess.post(
                f"{url}/api/admin/token",
                data={"username": username, "password": password},
            )
            if resp.status == 200:
                data = await resp.json()
                return data.get("access_token")
    except Exception as e:
        logger.debug(f"Marzban login failed for {url}: {e}")
    return None


async def check_server_health(srv: Server) -> dict:
    """Check single server health and update status."""
    password = decrypt_password(srv.marzban_password)
    token = await _marzban_login(srv.marzban_url, srv.marzban_username, password)

    now = datetime.utcnow()
    async with async_session() as session:
        db_srv = (await session.execute(
            select(Server).where(Server.id == srv.id)
        )).scalar_one_or_none()
        if not db_srv:
            return {"status": "offline"}

        if token:
            db_srv.status = "online"
            db_srv.last_check_at = now
            # Fetch stats
            try:
                stats = await _fetch_server_stats(srv.marzban_url, token)
                db_srv.current_users = stats.get("current_users", 0)
                db_srv.total_bandwidth = stats.get("total_bandwidth", 0)
            except Exception:
                pass
            await session.commit()
            return {"status": "online", "last_check": now.isoformat()}
        else:
            db_srv.status = "offline"
            db_srv.last_check_at = now
            await session.commit()
            return {"status": "offline", "last_check": now.isoformat()}


async def _fetch_server_stats(url: str, token: str) -> dict:
    """Fetch system stats from Marzban API."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as sess:
            resp = await sess.get(
                f"{url}/api/system/stats",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        logger.debug(f"Stats fetch failed for {url}: {e}")
    return {}


async def check_all_health() -> list[dict]:
    """Check health of all active servers."""
    servers = await get_all_servers()
    results = []
    for srv in servers:
        if not srv.is_active:
            continue
        result = await check_server_health(srv)
        results.append({"id": srv.id, "name": srv.name, **result})
    return results


async def get_server_stats(server_id: int) -> Optional[dict]:
    """Get detailed stats for a server."""
    srv = await get_server(server_id)
    if not srv:
        return None

    password = decrypt_password(srv.marzban_password)
    token = await _marzban_login(srv.marzban_url, srv.marzban_username, password)
    if not token:
        return {"server_id": server_id, "status": "offline"}

    stats = await _fetch_server_stats(srv.marzban_url, token)
    return {
        "server_id": server_id,
        "name": srv.name,
        "status": "online",
        "url": srv.marzban_url,
        "country": srv.country,
        "city": srv.city,
        "ip_address": srv.ip_address,
        "is_master": srv.is_master,
        "current_users": srv.current_users,
        "max_users": srv.max_users,
        "total_bandwidth": srv.total_bandwidth,
        "last_check_at": srv.last_check_at.isoformat() if srv.last_check_at else None,
        "marzban_stats": stats,
    }


async def sync_all_servers() -> dict:
    """Trigger sync for all active servers. Returns summary."""
    servers = await get_all_servers()
    results = {}
    for srv in servers:
        if not srv.is_active:
            continue
        password = decrypt_password(srv.marzban_password)
        token = await _marzban_login(srv.marzban_url, srv.marzban_username, password)
        if token:
            results[srv.name] = {"status": "connected"}
        else:
            results[srv.name] = {"status": "failed"}
    return results


# Background health checker
_health_task: Optional[asyncio.Task] = None


async def start_health_checker(interval_seconds: int = 300):
    """Start periodic health checks (every 5 min by default)."""
    global _health_task
    if _health_task and not _health_task.done():
        return

    async def _loop():
        while True:
            try:
                await check_all_health()
            except Exception as e:
                logger.error(f"Health check error: {e}")
            await asyncio.sleep(interval_seconds)

    _health_task = asyncio.create_task(_loop())
    logger.info(f"Server health checker started (interval={interval_seconds}s)")
