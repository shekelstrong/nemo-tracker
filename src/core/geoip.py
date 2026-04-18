"""GeoIP resolver — MaxMind GeoLite2 with ip-api.com fallback."""

import time
import asyncio
from typing import Optional

import aiohttp
from loguru import logger

from src.config import settings

_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 3600  # 1 hour

_mmdb_reader = None


def _get_mmdb_reader():
    global _mmdb_reader
    if _mmdb_reader is not None:
        return _mmdb_reader
    import pathlib
    p = pathlib.Path(settings.geoip_db_path)
    if p.exists():
        try:
            import maxminddb
            _mmdb_reader = maxminddb.open_database(str(p))
            logger.info(f"GeoIP: Loaded MaxMind DB from {p}")
            return _mmdb_reader
        except Exception as e:
            logger.warning(f"GeoIP: Failed to load MaxMind DB: {e}")
    return None


def _lookup_mmdb(ip: str) -> Optional[dict]:
    reader = _get_mmdb_reader()
    if not reader:
        return None
    try:
        result = reader.get(ip)
        if not result:
            return None
        country = result.get("country", {})
        city_info = result.get("city", {})
        loc = result.get("location", {})
        return {
            "country": country.get("iso_code"),
            "city": city_info.get("names", {}).get("en"),
            "lat": loc.get("latitude"),
            "lon": loc.get("longitude"),
        }
    except Exception:
        return None


async def _lookup_api(ip: str) -> Optional[dict]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,lat,lon",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                data = await resp.json()
                if data.get("status") != "success":
                    return None
                return {
                    "country": data.get("countryCode"),
                    "city": data.get("city"),
                    "lat": data.get("lat"),
                    "lon": data.get("lon"),
                }
    except Exception as e:
        logger.warning(f"GeoIP ip-api lookup failed for {ip}: {e}")
        return None


async def get_geo(ip: str) -> dict:
    """Resolve IP geolocation. Returns {country, city, lat, lon}."""
    if not ip or ip in ("0.0.0.0", "127.0.0.1", "::1"):
        return {"country": None, "city": None, "lat": None, "lon": None}

    now = time.time()
    cached = _cache.get(ip)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]

    # Try MaxMind first (sync, fast)
    result = _lookup_mmdb(ip)

    # Fallback to ip-api
    if not result:
        result = await _lookup_api(ip)

    if not result:
        result = {"country": None, "city": None, "lat": None, "lon": None}

    _cache[ip] = (now, result)
    return result
