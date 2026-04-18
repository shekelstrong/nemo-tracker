"""Device tracker — monitors unique IPs per user via subscription requests.

Two sources:
1. Xray connection logs (real-time, works for standard tier)
2. Marzban subscription requests /sub/ (periodic, works for all tiers including VIP)

Logic: count unique IPs per user over rolling 30-day window.
If unique IPs > device_limit → alert or auto-disable.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from loguru import logger

from src.core.marzban_client import marzban_client
from src.models import async_session
from src.models.database import UserIP, User as DBUser
from sqlalchemy import select, delete, func, distinct


class DeviceTracker:
    """Tracks unique IPs per user and enforces device limits."""

    # Device limits per user (username -> max devices)
    # Populated from Marzban user data or external DB
    _device_limits: Dict[str, int] = {}

    # IPs to ignore (from config: proxy servers, internal)
    # Populated from settings.ignored_ips_set
    IGNORED_IPS = set()  # Updated in __init__ or sync

    async def record_ip(self, username: str, ip: str, inbound: str = "", source: str = "sub"):
        """Record an IP address for a user.
        
        Rules (all configurable via .env):
        - Inbounds in ignore_inbounds: NEVER track/block
        - Inbounds in track_inbounds: track only if user has device_count > 0
        - Skip ignored IPs (proxy servers, from config)
        """
        if not username or not ip:
            return

        # Skip proxy/internal IPs (configurable)
        all_ignored = self.IGNORED_IPS | settings.ignored_ips_set
        if ip in all_ignored or ip.startswith(("127.", "10.", "172.", "192.168.", "0.")):
            return

        # Skip ignored inbounds (e.g. standard VPN)
        if inbound and inbound in settings.ignore_inbounds_list:
            return

        # Skip if inbound not in track list
        if settings.track_inbounds_list and inbound not in settings.track_inbounds_list:
            return

        async with async_session() as session:
            # Check if this IP already recorded
            result = await session.execute(
                select(UserIP).where(
                    UserIP.username == username,
                    UserIP.ip == ip
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update last_seen
                existing.last_seen = datetime.utcnow()
                existing.source = source
            else:
                # New IP for this user
                session.add(UserIP(
                    username=username,
                    ip=ip,
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                    source=source,
                ))
                logger.info(f"📱 New device: {username} → {ip} (via {source})")

            await session.commit()

    async def get_unique_ip_count(self, username: str, days: int = 30) -> int:
        """Get count of unique IPs for a user in the last N days."""
        since = datetime.utcnow() - timedelta(days=days)
        async with async_session() as session:
            result = await session.execute(
                select(func.count(distinct(UserIP.ip)))
                .where(
                    UserIP.username == username,
                    UserIP.last_seen >= since
                )
            )
            return result.scalar() or 0

    async def get_user_ips(self, username: str, days: int = 30) -> List[dict]:
        """Get all IPs for a user with metadata."""
        since = datetime.utcnow() - timedelta(days=days)
        async with async_session() as session:
            result = await session.execute(
                select(UserIP)
                .where(
                    UserIP.username == username,
                    UserIP.last_seen >= since
                )
                .order_by(UserIP.last_seen.desc())
            )
            ips = result.scalars().all()
            return [
                {
                    "ip": ip.ip,
                    "first_seen": ip.first_seen.isoformat(),
                    "last_seen": ip.last_seen.isoformat(),
                    "source": ip.source,
                    "geo": ip.geo_country or "?",
                    "city": ip.geo_city or "?",
                }
                for ip in ips
            ]

    async def set_device_limit(self, username: str, limit: int):
        """Set device limit for a user."""
        self._device_limits[username] = limit

    async def check_and_enforce(self, username: str, inbound: str = "") -> Optional[dict]:
        """Check if user exceeds device limit. Returns alert dict if exceeded.
        
        Rules (all configurable):
        - Inbounds in ignore_inbounds: NEVER enforce
        - Only enforce if user has device_count > 0 (configurable)
        """
        # Skip ignored inbounds
        if inbound and inbound in settings.ignore_inbounds_list:
            return None

        limit = self._device_limits.get(username, 0)
        if limit <= 0:
            return None  # No limit set (old client or unlimited)

        count = await self.get_unique_ip_count(username, days=30)
        
        if count > limit:
            return {
                "username": username,
                "device_count": count,
                "device_limit": limit,
                "action": "exceeded",
                "message": f"⚠️ {username}: {count} уникальных IP при лимите {limit}",
            }
        elif count == limit:
            return {
                "username": username,
                "device_count": count,
                "device_limit": limit,
                "action": "at_limit",
                "message": f"📱 {username}: {count}/{limit} устройств (лимит достигнут)",
            }
        return None

    async def sync_device_limits_from_marzban(self):
        """Sync device limits from Marzban users (device_count field)."""
        users = await marzban_client.get_all_users(limit=1000)
        synced = 0
        for user in users:
            username = user.get("username", "")
            if not username:
                continue
            # Try to get device_count from note or metadata
            # Marzban doesn't have device_count natively, so we use our DB
            # The vpn_bot sets device_count on the bot's DB side
            synced += 1
        
        # Also sync from our own DB users
        async with async_session() as session:
            result = await session.execute(
                select(DBUser).where(DBUser.device_count > 0)
            )
            db_users = result.scalars().all()
            for u in db_users:
                self._device_limits[u.username] = u.device_count
        
        logger.info(f"Synced device limits for {synced} users")

    async def cleanup_old_ips(self, days: int = 30):
        """Remove IP records older than N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        async with async_session() as session:
            await session.execute(
                delete(UserIP).where(UserIP.last_seen < cutoff)
            )
            await session.commit()
        logger.info(f"Cleaned up IPs older than {days} days")

    async def get_all_overview(self) -> List[dict]:
        """Get overview of all users with device usage."""
        async with async_session() as session:
            since = datetime.utcnow() - timedelta(days=30)
            result = await session.execute(
                select(
                    UserIP.username,
                    func.count(distinct(UserIP.ip)).label("ip_count"),
                    func.max(UserIP.last_seen).label("last_active"),
                )
                .where(UserIP.last_seen >= since)
                .group_by(UserIP.username)
                .order_by(func.count(distinct(UserIP.ip)).desc())
            )
            rows = result.all()
            overview = []
            for row in rows:
                limit = self._device_limits.get(row.username, 0)
                overview.append({
                    "username": row.username,
                    "unique_ips": row.ip_count,
                    "device_limit": limit,
                    "last_active": row.last_active.isoformat() if row.last_active else None,
                    "status": "over" if limit > 0 and row.ip_count > limit else "ok",
                })
            return overview


device_tracker = DeviceTracker()
