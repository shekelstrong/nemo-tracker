"""Xray log stream reader via Marzban WebSocket API.

Connects to Marzban's /api/core/logs WebSocket endpoint and parses
VPN connection events in real-time. No log files needed.
"""

import re
import asyncio
from datetime import datetime
from typing import Optional, Callable, Awaitable
from loguru import logger

try:
    import websockets
except ImportError:
    websockets = None

from src.core.marzban_client import marzban_client
from src.config import settings


# Pattern: 2026/04/18 05:45:58.111225 from 51.250.40.213:44610 accepted tcp:104.21.42.37:443 [vless-reality-whitelist >> direct] email: 101.l7HtaB
LOG_PATTERN = re.compile(
    r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})[\d.]*\s+"
    r"(?:from\s+)?(?:tcp:)?([\d.]+):(\d+)\s+"
    r"accepted\s+(\w+):([^\s]+)\s+"
    r"\[([^\]]+)\]"
    r"(?:\s+email:\s*(.+))?"
)

# Inbound tags
INBOUND_TAGS = {
    "vless-reality-standard": "standard",
    "vless-reality-whitelist": "premium",
}


class LogStreamReader:
    """Reads Xray logs via Marzban WebSocket in real-time."""

    def __init__(self):
        self._running = False
        self._on_connection: Optional[Callable] = None
        # Map: UUID -> username (cached from Marzban)
        self._uuid_to_user: dict[str, str] = {}

    def on_connection(self, func: Callable):
        """Register callback for new VPN connections.
        
        Callback receives: (ip, port, destination, inbound_tag, outbound, timestamp)
        """
        self._on_connection = func
        return func

    async def _ensure_user_cache(self):
        """Build UUID -> username mapping from Marzban."""
        users = await marzban_client.get_all_users(limit=1000)
        self._uuid_to_user.clear()
        for user in users:
            username = user.get("username", "")
            proxies = user.get("proxies", {})
            vless = proxies.get("vless", {})
            uuid = vless.get("id", "")
            if uuid and username:
                self._uuid_to_user[uuid] = username
        logger.info(f"Cached {len(self._uuid_to_user)} UUID -> username mappings")

    def _parse_log_line(self, line: str) -> Optional[dict]:
        """Parse an Xray log line into structured data."""
        match = LOG_PATTERN.search(line)
        if not match:
            return None

        timestamp_str, ip, port, protocol, dest, routing, email = match.groups()

        # Parse routing: "inbound >> outbound" or "inbound -> outbound"
        sep = ">>" if ">>" in routing else "->"
        parts = [p.strip() for p in routing.split(sep)]
        inbound = parts[0] if len(parts) >= 1 else ""
        outbound = parts[1] if len(parts) >= 2 else ""

        # Skip API and internal connections
        if "API_INBOUND" in inbound or inbound == "API":
            return None

        tier = INBOUND_TAGS.get(inbound, "unknown")

        # Clean email/username (e.g. "101.l7HtaB" or "77.user_278222385_20260328_113548")
        username = email.strip() if email else ""
        # Marzban email format: "INDEX.USERNAME" — extract just username
        if "." in username:
            username = username.split(".", 1)[1]

        try:
            ts = datetime.strptime(timestamp_str, "%Y/%m/%d %H:%M:%S")
        except ValueError:
            ts = datetime.utcnow()

        return {
            "ip": ip,
            "port": int(port),
            "protocol": protocol,
            "destination": dest,
            "inbound": inbound,
            "outbound": outbound.strip(),
            "tier": tier,
            "username": username,
            "timestamp": ts,
        }

    async def start(self):
        """Start reading logs from Marzban WebSocket."""
        if websockets is None:
            logger.error("websockets package not installed")
            return

        self._running = True
        await self._ensure_user_cache()

        while self._running:
            try:
                # Get auth token
                token_resp = await asyncio.to_thread(
                    lambda: __import__("httpx").post(
                        f"{settings.marzban_url}/api/admin/token",
                        data={
                            "username": settings.marzban_admin_username,
                            "password": settings.marzban_admin_password,
                        },
                        verify=False,
                    )
                )
                # Use marzban_client instead
                token = await self._get_token()
                
                base_url = settings.marzban_url.replace("http://", "ws://").replace("https://", "wss://")
                uri = f"{base_url}/api/core/logs?interval=1&token={token}"

                import ssl
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE

                logger.info(f"Connecting to Xray log stream: {base_url}")
                async with websockets.connect(uri, ssl=ssl_ctx, open_timeout=15) as ws:
                    logger.info("✅ Connected to Xray log stream")
                    async for msg in ws:
                        if not self._running:
                            break
                        parsed = self._parse_log_line(str(msg))
                        if parsed and self._on_connection:
                            await self._on_connection(parsed)

            except Exception as e:
                logger.error(f"Log stream error: {e}")
                if self._running:
                    logger.info("Reconnecting in 10 seconds...")
                    await asyncio.sleep(10)

    async def _get_token(self) -> str:
        """Get Marzban API token."""
        import httpx
        resp = await asyncio.to_thread(
            lambda: httpx.post(
                f"{settings.marzban_url}/api/admin/token",
                data={
                    "username": settings.marzban_admin_username,
                    "password": settings.marzban_admin_password,
                },
                verify=False,
            )
        )
        return resp.json()["access_token"]

    def stop(self):
        """Stop reading logs."""
        self._running = False
        logger.info("Log stream reader stopped")


log_reader = LogStreamReader()
