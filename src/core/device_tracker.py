"""Device tracker — monitors unique IPs per user."""

from datetime import datetime
from typing import Dict, List, Optional, Set
from loguru import logger

from src.core.marzban_client import marzban_client


class DeviceTracker:
    """Tracks unique IPs per Marzban user and enforces device limits."""

    # In-memory store: username -> set of IPs
    _user_ips: Dict[str, Set[str]] = {}
    # User device limits (fetched from external config or DB)
    _user_limits: Dict[str, int] = {}

    async def sync_users(self):
        """Fetch all users from Marzban and sync IP history."""
        users = await marzban_client.get_all_users(limit=1000)
        for user in users:
            username = user.get("username", "")
            # TODO: store in DB for persistence
        logger.info(f"Synced {len(users)} users from Marzban")

    async def check_user_devices(self, username: str) -> Dict:
        """Check current device count for a user."""
        user = await marzban_client.get_user(username)
        if not user:
            return {"error": "User not found"}

        # TODO: parse Xray logs or use Marzban active connections
        # For now, return basic info
        return {
            "username": username,
            "status": user.get("status"),
            "used_traffic": user.get("used_traffic", 0),
            "data_limit": user.get("data_limit", 0),
            "online_at": user.get("online_at"),
        }

    async def enforce_limit(self, username: str, max_devices: int) -> bool:
        """Disable user if they exceed device limit. Returns True if blocked."""
        # TODO: implement IP counting from logs
        return False


device_tracker = DeviceTracker()
