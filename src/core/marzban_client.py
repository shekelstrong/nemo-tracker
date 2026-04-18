"""Marzban API client for Nemo Tracker."""

import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from loguru import logger

from src.config import settings


class MarzbanClient:
    """Async client for Marzban API."""

    def __init__(self):
        base = settings.marzban_url.rstrip("/")
        if not base.endswith("/api"):
            base = f"{base}/api"
        self.base_url = base
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._client = httpx.AsyncClient(timeout=30.0, verify=False)

    async def _ensure_token(self) -> str:
        if self._token and self._token_expires and datetime.utcnow() < self._token_expires:
            return self._token
        resp = await self._client.post(
            f"{self.base_url}/admin/token",
            data={
                "username": settings.marzban_admin_username,
                "password": settings.marzban_admin_password,
            },
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        self._token_expires = datetime.utcnow() + timedelta(hours=23)
        return self._token

    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        token = await self._ensure_token()
        headers = {"Authorization": f"Bearer {token}"}
        resp = await self._client.request(
            method, f"{self.base_url}/{path.lstrip('/')}", headers=headers, **kwargs
        )
        resp.raise_for_status()
        return resp.json() if resp.status_code != 204 else {}

    # === Users ===

    async def get_all_users(self, offset: int = 0, limit: int = 100) -> List[Dict]:
        """Get all users from Marzban."""
        return (await self._request("GET", "/users", params={"offset": offset, "limit": limit})).get("users", [])

    async def get_user(self, username: str) -> Optional[Dict]:
        """Get single user data."""
        try:
            return await self._request("GET", f"/user/{username}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def disable_user(self, username: str) -> Dict:
        """Disable a user (block access)."""
        return await self._request("PUT", f"/user/{username}", json={"status": "disabled"})

    async def enable_user(self, username: str) -> Dict:
        """Re-enable a user."""
        return await self._request("PUT", f"/user/{username}", json={"status": "active"})

    async def get_user_usage(self, username: str) -> Dict:
        """Get user usage stats."""
        return await self._request("GET", f"/user/{username}/usage")

    # === System ===

    async def get_system_stats(self) -> Dict:
        """Get system statistics."""
        return await self._request("GET", "/system")

    async def get_nodes(self) -> List[Dict]:
        """Get all nodes."""
        return await self._request("GET", "/nodes")

    async def close(self):
        await self._client.aclose()


marzban_client = MarzbanClient()
