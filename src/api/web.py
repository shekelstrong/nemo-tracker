"""
Nemo Tracker — Web Admin Panel (FastAPI)
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

# ---------------------------------------------------------------------------
# App init
# ---------------------------------------------------------------------------

web_app = FastAPI(title="Nemo Tracker", docs_url=None, redoc_url=None)

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

web_app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))

from src.api.auth import router as auth_router, auth_middleware, ensure_default_admin
web_app.include_router(auth_router)
web_app.middleware("http")(auth_middleware)

# Make reseller routes accessible without admin auth
import src.api.auth as _auth_mod
_auth_mod.PUBLIC_PATHS.add("/r/panel")
# Monkeypatch prefix check to include /api/r/ and /r/
_orig_prefixes = _auth_mod.PUBLIC_PREFIXES
_auth_mod.PUBLIC_PREFIXES = _orig_prefixes + ("/api/r/", "/r/")

# ---------------------------------------------------------------------------
# DB imports (lazy to avoid circular imports at module level)
# ---------------------------------------------------------------------------

from src.models import async_session
from src.models.database import User as DBUser, Analytics, Alert, Connection
from src.core.marzban_client import marzban_client
from src.core.device_tracker import device_tracker
from src.core.geoip import get_geo
from sqlalchemy import select, func, desc, distinct, delete
from src.models.database import UserIP, PromoCode, TariffPlan, Reseller, ResellerTransaction, ResellerUser, AutoRenewal

# ---------------------------------------------------------------------------
# WebSocket manager
# ---------------------------------------------------------------------------

class WSManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.connections.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections.remove(ws)

ws_manager = WSManager()

# ---------------------------------------------------------------------------
# Settings file
# ---------------------------------------------------------------------------

SETTINGS_FILE = BASE_DIR / "data" / "settings.json"

def _default_settings() -> dict:
    return {
        "marzban_url": "",
        "marzban_username": "",
        "marzban_password": "",
        "telegram_token": "",
        "telegram_admin_ids": "",
        "track_inbounds": [],
        "ignore_inbounds": [],
        "ignored_ips": "",
        "notify_new_user": True,
        "notify_traffic_80": True,
        "notify_device_over": True,
        "notify_expiring": True,
    }

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text())
    return _default_settings()

def save_settings(data: dict):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_bytes(b: int) -> str:
    if b is None:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"

def _fmt_pct(used, limit):
    if not limit or limit <= 0:
        return 0
    return round((used / limit) * 100, 1)

# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@web_app.get("/", response_class=HTMLResponse)
async def page_dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")

@web_app.get("/users", response_class=HTMLResponse)
async def page_users(request: Request):
    return templates.TemplateResponse(request, "users.html")

@web_app.get("/users/{username}", response_class=HTMLResponse)
async def page_user_detail(request: Request, username: str):
    return templates.TemplateResponse(request, "user_detail.html", {"username": username})

@web_app.get("/devices", response_class=HTMLResponse)
async def page_devices(request: Request):
    return templates.TemplateResponse(request, "devices.html")

@web_app.get("/devices/{username}", response_class=HTMLResponse)
async def page_device_detail(request: Request, username: str):
    return templates.TemplateResponse(request, "user_detail.html", {"username": username, "tab": "devices"})

@web_app.get("/analytics", response_class=HTMLResponse)
async def page_analytics(request: Request):
    return templates.TemplateResponse(request, "analytics.html")

@web_app.get("/settings", response_class=HTMLResponse)
async def page_settings(request: Request):
    return templates.TemplateResponse(request, "settings.html")

@web_app.get("/alerts", response_class=HTMLResponse)
async def page_alerts(request: Request):
    return templates.TemplateResponse(request, "alerts.html")

@web_app.get("/finance", response_class=HTMLResponse)
async def page_finance(request: Request):
    return templates.TemplateResponse(request, "finance.html")

@web_app.get("/export", response_class=HTMLResponse)
async def page_export(request: Request):
    return templates.TemplateResponse(request, "export.html")

@web_app.get("/geo", response_class=HTMLResponse)
async def page_geo(request: Request):
    return templates.TemplateResponse(request, "geo.html")

# ---------------------------------------------------------------------------
# API routes — REAL DATA
# ---------------------------------------------------------------------------

@web_app.get("/auto-renewal", response_class=HTMLResponse)
async def page_auto_renewal(request: Request):
    return templates.TemplateResponse(request, "auto_renewal.html")


@web_app.get("/api/auto-renewal")
async def api_auto_renewal_list():
    async with async_session() as session:
        rows = (await session.execute(
            select(AutoRenewal).order_by(desc(AutoRenewal.created_at))
        )).scalars().all()
        result = []
        for ar in rows:
            tariff = (await session.execute(
                select(TariffPlan).where(TariffPlan.id == ar.tariff_id)
            )).scalar_one_or_none() if ar.tariff_id else None
            result.append({
                "id": ar.id,
                "username": ar.username,
                "telegram_id": ar.telegram_id,
                "tariff_id": ar.tariff_id,
                "tariff_name": tariff.name if tariff else None,
                "payment_method": ar.payment_method,
                "is_active": ar.is_active,
                "last_renewed_at": ar.last_renewed_at.isoformat() if ar.last_renewed_at else None,
                "next_renewal_at": ar.next_renewal_at.isoformat() if ar.next_renewal_at else None,
                "fail_count": ar.fail_count,
                "created_at": ar.created_at.isoformat() if ar.created_at else None,
            })
        return result


@web_app.post("/api/auto-renewal/{username}/enable")
async def api_auto_renewal_enable(username: str, request: Request):
    data = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    async with async_session() as session:
        existing = (await session.execute(
            select(AutoRenewal).where(AutoRenewal.username == username)
        )).scalar_one_or_none()
        if existing:
            existing.is_active = True
            existing.fail_count = 0
            if data.get("tariff_id"):
                existing.tariff_id = int(data["tariff_id"])
            if data.get("payment_method"):
                existing.payment_method = data["payment_method"]
            if data.get("telegram_id"):
                existing.telegram_id = int(data["telegram_id"])
        else:
            # Get user info for defaults
            db_user = (await session.execute(
                select(DBUser).where(DBUser.username == username)
            )).scalar_one_or_none()
            tariff_id = int(data["tariff_id"]) if data.get("tariff_id") else None
            # Calculate next_renewal_at from user expire
            next_renewal = None
            if db_user and db_user.expire:
                tariff = None
                if tariff_id:
                    tariff = (await session.execute(
                        select(TariffPlan).where(TariffPlan.id == tariff_id)
                    )).scalar_one_or_none()
                days = tariff.duration_days if tariff else 30
                if db_user.expire > datetime.utcnow():
                    next_renewal = db_user.expire - timedelta(days=1)  # renew 1 day before expiry
                else:
                    next_renewal = datetime.utcnow() + timedelta(hours=1)
            ar = AutoRenewal(
                username=username,
                telegram_id=int(data["telegram_id"]) if data.get("telegram_id") else None,
                tariff_id=tariff_id,
                payment_method=data.get("payment_method", "cryptopay"),
                is_active=True,
                next_renewal_at=next_renewal,
            )
            session.add(ar)
        await session.commit()
        return {"ok": True}


@web_app.post("/api/auto-renewal/{username}/disable")
async def api_auto_renewal_disable(username: str):
    async with async_session() as session:
        ar = (await session.execute(
            select(AutoRenewal).where(AutoRenewal.username == username)
        )).scalar_one_or_none()
        if not ar:
            raise HTTPException(404, "Auto-renewal not found for this user")
        ar.is_active = False
        await session.commit()
        return {"ok": True}


@web_app.get("/api/auto-renewal/stats")
async def api_auto_renewal_stats():
    async with async_session() as session:
        total = await session.scalar(select(func.count(AutoRenewal.id)))
        active = await session.scalar(
            select(func.count(AutoRenewal.id)).where(AutoRenewal.is_active == True)
        )
        failures = await session.scalar(
            select(func.count(AutoRenewal.id)).where(AutoRenewal.fail_count > 0)
        )
        # Revenue from auto-renewals (transactions with description 'Auto-renewal')
        revenue = await session.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .where(Transaction.description == "Auto-renewal", Transaction.status == "paid")
        )
        return {
            "total": total or 0,
            "active": active or 0,
            "inactive": (total or 0) - (active or 0),
            "revenue": float(revenue or 0),
            "failures": failures or 0,
            "failure_rate": round((failures or 0) / max(total or 1, 1) * 100, 1),
        }


@web_app.get("/promocodes", response_class=HTMLResponse)
async def page_promocodes(request: Request):
    return templates.TemplateResponse(request, "promocodes.html")


@web_app.get("/tariffs", response_class=HTMLResponse)
async def page_tariffs(request: Request):
    return templates.TemplateResponse(request, "tariffs.html")


@web_app.get("/api/dashboard")
async def api_dashboard():
    async with async_session() as session:
        # Stats
        total = await session.scalar(select(func.count(DBUser.id)))
        active = await session.scalar(
            select(func.count(DBUser.id)).where(DBUser.status == "active")
        )
        online = await session.scalar(
            select(func.count(DBUser.id)).where(DBUser.status == "active", DBUser.was_online == True)
        )
        total_traffic = await session.scalar(
            select(func.coalesce(func.sum(DBUser.used_traffic), 0))
        )

        # Recent analytics for charts
        now = datetime.utcnow()
        analytics_rows = (await session.execute(
            select(Analytics).order_by(desc(Analytics.date)).limit(30)
        )).scalars().all()

        traffic_30d = []
        user_growth = []
        for row in reversed(analytics_rows):
            d = row.date.strftime("%b %d") if hasattr(row.date, 'strftime') else str(row.date)
            traffic_30d.append({"day": d, "value": round(row.total_traffic_gb, 1) if row.total_traffic_gb else 0})
            user_growth.append({"date": d, "total": row.total_users, "active": row.active_users})

        # Online over last 24h from connections
        since_24h = now - timedelta(hours=24)
        online_data = (await session.execute(
            select(
                func.date_trunc("hour", Connection.online_at).label("hour"),
                func.count(distinct(Connection.username)).label("count")
            )
            .where(Connection.online_at >= since_24h)
            .group_by("hour")
            .order_by("hour")
        )).all()
        online_24h = [{"hour": r.hour.strftime("%H:00") if hasattr(r.hour, 'strftime') else str(r.hour),
                        "count": r.count} for r in online_data]

        # If no connection data yet, use current online count
        if not online_24h:
            online_24h = [{"hour": f"{(now - timedelta(hours=i)).strftime('%H:00')}",
                           "count": online or 0} for i in range(24)]

        # Peak hours (from connections, last 7 days)
        since_7d = now - timedelta(days=7)
        peak_rows = (await session.execute(
            select(
                func.extract("hour", Connection.online_at).label("h"),
                func.count().label("cnt")
            )
            .where(Connection.online_at >= since_7d)
            .group_by("h")
            .order_by("h")
        )).all()
        peak_hours = {"labels": [], "values": []}
        for r in peak_rows:
            h = int(r.h)
            peak_hours["labels"].append(f"{h:02d}-{h+1:02d}" if h < 23 else "23-00")
            peak_hours["values"].append(r.cnt)
        if not peak_hours["labels"]:
            peak_hours = {"labels": ["00-04","04-08","08-12","12-16","16-20","20-24"],
                          "values": [0,0,0,0,0,0]}

        # Recent alerts
        recent_alerts = (await session.execute(
            select(Alert).order_by(desc(Alert.created_at)).limit(10)
        )).scalars().all()
        alerts_list = []
        for a in recent_alerts:
            age = now - a.created_at.replace(tzinfo=None) if a.created_at else timedelta()
            if age.total_seconds() < 60:
                time_str = "just now"
            elif age.total_seconds() < 3600:
                time_str = f"{int(age.total_seconds()/60)} min ago"
            elif age.total_seconds() < 86400:
                time_str = f"{int(age.total_seconds()/3600)} hr ago"
            else:
                time_str = f"{int(age.total_seconds()/86400)}d ago"
            alerts_list.append({
                "type": a.alert_type,
                "message": a.message,
                "time": time_str,
            })

        return {
            "stats": {
                "total_users": total or 0,
                "active_users": active or 0,
                "online_now": online or 0,
                "total_traffic": _fmt_bytes(total_traffic or 0),
            },
            "online_24h": online_24h,
            "traffic_30d": traffic_30d,
            "growth": user_growth,
            "peak_hours": peak_hours,
            "recent_alerts": alerts_list,
        }


@web_app.get("/api/users")
async def api_users():
    async with async_session() as session:
        rows = (await session.execute(
            select(DBUser).order_by(desc(DBUser.was_online), DBUser.username)
        )).scalars().all()

        users = []
        for u in rows:
            traffic_pct = _fmt_pct(u.used_traffic or 0, u.data_limit) if u.data_limit else None
            users.append({
                "username": u.username,
                "status": u.status,
                "traffic_used_gb": round((u.used_traffic or 0) / 1024**3, 2),
                "traffic_limit_gb": round((u.data_limit or 0) / 1024**3, 2) if u.data_limit else None,
                "traffic_pct": traffic_pct,
                "devices": u.device_count or 0,
                "last_online": u.online_at.isoformat() if u.online_at else None,
                "expire": u.expire.strftime("%d.%m.%Y") if u.expire else None,
                "tier": u.tier or 0,
                "tier_name": "Premium" if (u.tier or 0) >= 1 else "Стандарт",
            })
        return users


@web_app.get("/api/users/{username}")
async def api_user_detail(username: str):
    async with async_session() as session:
        user = (await session.execute(
            select(DBUser).where(DBUser.username == username)
        )).scalar_one_or_none()

        if not user:
            raise HTTPException(404, "User not found")

        # Traffic 7d (from analytics or user data)
        now = datetime.utcnow()
        traffic_7d = [{"day": (now - timedelta(days=6-i)).strftime("%b %d"),
                        "dl": round((user.used_traffic or 0) / 1024**3 / 7, 2),
                        "ul": 0} for i in range(7)]

        # IP history
        from src.models.database import UserIP
        ips = (await session.execute(
            select(UserIP).where(UserIP.username == username).order_by(desc(UserIP.last_seen)).limit(20)
        )).scalars().all()
        ip_history = [{"ip": ip.ip, "country": ip.geo_country or "?", "city": ip.geo_city or "?",
                        "first": ip.first_seen.strftime("%Y-%m-%d %H:%M") if ip.first_seen else "?",
                        "last": ip.last_seen.strftime("%Y-%m-%d %H:%M") if ip.last_seen else "?"} for ip in ips]

        # Recent connections
        conns = (await session.execute(
            select(Connection).where(Connection.username == username).order_by(desc(Connection.online_at)).limit(10)
        )).scalars().all()
        connections = [{"time": c.online_at.strftime("%Y-%m-%d %H:%M") if c.online_at else "?",
                         "ip": "", "duration": f"{c.duration_min:.0f} min" if c.duration_min else "?"} for c in conns]

        return {
            "username": user.username,
            "status": user.status,
            "traffic_used_gb": round((user.used_traffic or 0) / 1024**3, 2),
            "traffic_limit_gb": round((user.data_limit or 0) / 1024**3, 2) if user.data_limit else None,
            "devices": len(ip_history),
            "device_limit": user.device_count or 0,
            "created": user.created_at.strftime("%d.%m.%Y") if user.created_at else "?",
            "expire": user.expire.strftime("%d.%m.%Y") if user.expire else None,
            "tier": user.tier or 0,
            "tier_name": "Premium" if (user.tier or 0) >= 1 else "Стандарт",
            "traffic_7d": traffic_7d,
            "ip_history": ip_history,
            "connections": connections,
        }


# ---------------------------------------------------------------------------
# API routes — User management (Marzban)
# ---------------------------------------------------------------------------

@web_app.post("/api/users")
async def api_create_user(request: Request):
    data = await request.json()
    username = data.get("username")
    if not username:
        raise HTTPException(400, "username is required")
    data_limit_gb = data.get("data_limit_gb")
    months = data.get("months", 1)
    ip_limit = data.get("ip_limit")
    note = data.get("note")

    data_limit_bytes = int(data_limit_gb * 1024**3) if data_limit_gb else None
    expire_date = int((datetime.utcnow() + timedelta(days=months * 30)).timestamp()) if months else None

    try:
        user = await marzban_client.create_user(
            username=username,
            data_limit_bytes=data_limit_bytes,
            expire_date=expire_date,
            ip_limit=ip_limit,
            note=note,
        )
        return user
    except Exception as e:
        logger.error(f"Create user error: {e}")
        raise HTTPException(500, str(e))


@web_app.put("/api/users/{username}")
async def api_update_user(username: str, request: Request):
    data = await request.json()
    
    # Update device_count in Nemo Tracker DB
    if "device_count" in data:
        async with async_session() as session:
            user = (await session.execute(
                select(DBUser).where(DBUser.username == username)
            )).scalar_one_or_none()
            if user:
                user.device_count = int(data["device_count"])
                await session.commit()
                # Update device_tracker limits
                from src.core.device_tracker import device_tracker
                await device_tracker.set_device_limit(username, int(data["device_count"]))
    
    payload = {}
    if "data_limit_gb" in data:
        payload["data_limit"] = int(data["data_limit_gb"] * 1024**3) if data["data_limit_gb"] else 0
    if "expire" in data:
        payload["expire"] = int(data["expire"]) if data["expire"] else 0
    if "note" in data:
        payload["note"] = data["note"]
    if "status" in data:
        payload["status"] = data["status"]
    try:
        if payload:
            return await marzban_client.update_user(username, **payload)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise HTTPException(500, str(e))


@web_app.delete("/api/users/{username}")
async def api_delete_user(username: str):
    try:
        await marzban_client.delete_user(username)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(500, str(e))


@web_app.post("/api/users/{username}/reset-traffic")
async def api_reset_traffic(username: str):
    try:
        return await marzban_client.reset_user_traffic(username)
    except Exception as e:
        logger.error(f"Reset traffic error: {e}")
        raise HTTPException(500, str(e))


@web_app.post("/api/users/{username}/toggle")
async def api_toggle_user(username: str, request: Request):
    data = await request.json()
    status = data.get("status")
    if status not in ("active", "disabled"):
        raise HTTPException(400, "status must be active or disabled")
    try:
        return await marzban_client.update_user(username, status=status)
    except Exception as e:
        logger.error(f"Toggle user error: {e}")
        raise HTTPException(500, str(e))


@web_app.get("/api/users/{username}/subscription")
async def api_get_subscription(username: str):
    try:
        url = await marzban_client.get_user_subscription_url(username)
        if not url:
            raise HTTPException(404, "Subscription URL not found")
        return {"url": url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get subscription error: {e}")
        raise HTTPException(500, str(e))


@web_app.get("/api/devices")
async def api_devices():
    overview = await device_tracker.get_all_overview()
    return overview


@web_app.get("/api/devices/{username}")
async def api_device_detail(username: str):
    ips = await device_tracker.get_user_ips(username)
    limit = device_tracker._device_limits.get(username, 0)
    return {
        "username": username,
        "device_limit": limit,
        "ips": ips,
    }


@web_app.get("/api/alerts")
async def api_alerts(type: Optional[str] = None, resolved: Optional[bool] = None):
    async with async_session() as session:
        q = select(Alert).order_by(desc(Alert.created_at)).limit(100)
        if type:
            q = q.where(Alert.alert_type == type)
        if resolved is not None:
            q = q.where(Alert.resolved == resolved)
        rows = (await session.execute(q)).scalars().all()
        return [
            {"id": a.id, "type": a.alert_type, "message": a.message,
             "time": a.created_at.isoformat() if a.created_at else None,
             "resolved": a.resolved}
            for a in rows
        ]


@web_app.post("/api/alerts/{alert_id}/resolve")
async def api_resolve_alert(alert_id: int):
    async with async_session() as session:
        alert = (await session.execute(
            select(Alert).where(Alert.id == alert_id)
        )).scalar_one_or_none()
        if alert:
            alert.resolved = True
            await session.commit()
            return {"ok": True}
        raise HTTPException(404, "Alert not found")


@web_app.get("/api/settings")
async def api_get_settings():
    return load_settings()


@web_app.post("/api/settings")
async def api_save_settings(request: Request):
    data = await request.json()
    save_settings(data)
    return {"ok": True}


@web_app.post("/api/settings/test-marzban")
async def api_test_marzban():
    try:
        token = await marzban_client.get_token()
        if token:
            return {"ok": True, "message": "Connected successfully"}
        return {"ok": False, "message": "Invalid credentials"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


@web_app.post("/api/settings/test-telegram")
async def api_test_telegram():
    # TODO: real bot test
    await asyncio.sleep(0.5)
    return {"ok": True, "message": "Bot token valid"}


# ---------------------------------------------------------------------------
# API routes — Analytics
# ---------------------------------------------------------------------------

@web_app.get("/api/analytics/traffic")
async def api_analytics_traffic():
    """Traffic data for last 30 days from analytics table."""
    async with async_session() as session:
        now = datetime.utcnow()
        rows = (await session.execute(
            select(Analytics)
            .where(Analytics.date >= (now - timedelta(days=30)).date())
            .order_by(Analytics.date)
        )).scalars().all()

        traffic = []
        for r in rows:
            traffic.append({
                "date": r.date.strftime("%Y-%m-%d") if hasattr(r.date, "strftime") else str(r.date),
                "total_gb": round(r.total_traffic_gb or 0, 2),
            })
        return traffic


@web_app.get("/api/analytics/top-users")
async def api_analytics_top_users():
    """Top-10 traffic consumers."""
    async with async_session() as session:
        rows = (await session.execute(
            select(DBUser)
            .where(DBUser.data_limit != None, DBUser.data_limit > 0)
            .order_by(desc(DBUser.used_traffic))
            .limit(10)
        )).scalars().all()

        result = []
        for u in rows:
            used_gb = round((u.used_traffic or 0) / 1024**3, 2)
            limit_gb = round((u.data_limit or 0) / 1024**3, 2)
            pct = round((used_gb / limit_gb) * 100, 1) if limit_gb > 0 else 0
            result.append({
                "username": u.username,
                "used_gb": used_gb,
                "limit_gb": limit_gb,
                "percent": pct,
            })
        return result


@web_app.get("/api/analytics/distribution")
async def api_analytics_distribution():
    """Distribution of users by traffic usage percentage buckets."""
    async with async_session() as session:
        rows = (await session.execute(
            select(DBUser.used_traffic, DBUser.data_limit)
            .where(DBUser.data_limit != None, DBUser.data_limit > 0)
        )).all()

        buckets = {"0-25": 0, "25-50": 0, "50-75": 0, "75-100": 0, ">100": 0}
        for used, limit in rows:
            pct = ((used or 0) / limit) * 100 if limit else 0
            if pct <= 25:
                buckets["0-25"] += 1
            elif pct <= 50:
                buckets["25-50"] += 1
            elif pct <= 75:
                buckets["50-75"] += 1
            elif pct <= 100:
                buckets["75-100"] += 1
            else:
                buckets[">100"] += 1

        return [{"range": k, "count": v} for k, v in buckets.items()]


@web_app.get("/api/analytics/anomalies")
async def api_analytics_anomalies():
    """Users with anomalous traffic consumption (>3x average)."""
    async with async_session() as session:
        rows = (await session.execute(
            select(DBUser).where(DBUser.status == "active")
        )).scalars().all()

        if not rows:
            return []

        used_values = [(u.used_traffic or 0) for u in rows if (u.used_traffic or 0) > 0]
        if not used_values:
            return []

        avg_traffic = sum(used_values) / len(used_values)
        threshold = avg_traffic * 3

        anomalies = []
        for u in rows:
            used = u.used_traffic or 0
            if used > threshold:
                used_gb = round(used / 1024**3, 2)
                limit_gb = round((u.data_limit or 0) / 1024**3, 2) if u.data_limit else None
                avg_gb = round(avg_traffic / 1024**3, 2)
                multiplier = round(used / avg_traffic, 1) if avg_traffic > 0 else 0
                anomalies.append({
                    "username": u.username,
                    "used_gb": used_gb,
                    "limit_gb": limit_gb,
                    "avg_gb": avg_gb,
                    "multiplier": multiplier,
                })

        return sorted(anomalies, key=lambda x: x["multiplier"], reverse=True)[:10]


# ---------------------------------------------------------------------------
# API routes — Finance (mock data)
# ---------------------------------------------------------------------------

import random

def _mock_transactions(count=20):
    names = ["alice", "bob", "charlie", "diana", "evgeny", "fedor", "greta", "hugo", "ira", "jake",
             "kate", "leo", "mike", "nina", "oleg", "pavel", "rita", "sergey", "tanya", "ivan"]
    methods = ["cryptopay", "platega"]
    statuses = ["paid"] * 8 + ["pending"] + ["failed"]
    txs = []
    now = datetime.utcnow()
    for i in range(count):
        days_ago = i // 2
        hrs = random.randint(0, 23)
        ts = now - timedelta(days=days_ago, hours=hrs)
        method = random.choice(methods)
        if method == "cryptopay":
            amount = round(random.uniform(3.0, 5.5), 2)
            currency = "USDT"
        else:
            amount = random.choice([300, 350, 399, 450, 499, 550, 599])
            currency = "RUB"
        txs.append({
            "id": 1000 + count - i,
            "username": random.choice(names),
            "amount": amount,
            "currency": currency,
            "payment_method": method,
            "status": random.choice(statuses),
            "description": "VPN subscription" if random.random() > 0.3 else "Renewal",
            "created_at": ts.isoformat(),
        })
    return txs


def _mock_chart_data(rate=95.0):
    now = datetime.utcnow()
    days = []
    for i in range(29, -1, -1):
        d = now - timedelta(days=i)
        rub = random.randint(800, 3500)
        usdt = round(rub / rate, 2)
        days.append({
            "date": d.strftime("%b %d"),
            "rub": rub,
            "usdt": usdt,
            "transactions": random.randint(2, 8),
        })
    return days


@web_app.get("/api/finance/summary")
async def api_finance_summary():
    from src.config import settings
    from src.models.database import Transaction
    rate = await settings.get_usdt_rub_rate()
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    
    async with async_session() as session:
        # All paid transactions
        all_result = await session.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .where(Transaction.status == "paid")
        )
        all_rub = float(all_result.scalar() or 0)
        
        # Today
        today_result = await session.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .where(Transaction.status == "paid", Transaction.created_at >= today_start)
        )
        today_rub = float(today_result.scalar() or 0)
        
        # This week
        week_result = await session.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .where(Transaction.status == "paid", Transaction.created_at >= week_start)
        )
        week_rub = float(week_result.scalar() or 0)
        
        # This month
        month_result = await session.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .where(Transaction.status == "paid", Transaction.created_at >= month_start)
        )
        month_rub = float(month_result.scalar() or 0)
    
    return {
        "today": {"rub": round(today_rub, 2), "usdt": round(today_rub / rate, 2)},
        "week": {"rub": round(week_rub, 2), "usdt": round(week_rub / rate, 2)},
        "month": {"rub": round(month_rub, 2), "usdt": round(month_rub / rate, 2)},
        "all_time": {"rub": round(all_rub, 2), "usdt": round(all_rub / rate, 2)},
        "rate": rate,
    }


@web_app.get("/api/finance/chart")
async def api_finance_chart():
    from src.models.database import Transaction
    now = datetime.utcnow()
    days = []
    for i in range(29, -1, -1):
        d = now - timedelta(days=i)
        day_start = d.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        async with async_session() as session:
            result = await session.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0))
                .where(Transaction.status == "paid", Transaction.created_at >= day_start, Transaction.created_at < day_end)
            )
            rub = float(result.scalar() or 0)
            count_result = await session.execute(
                select(func.count())
                .where(Transaction.status == "paid", Transaction.created_at >= day_start, Transaction.created_at < day_end)
            )
            cnt = count_result.scalar() or 0
        days.append({"date": d.strftime("%d.%m"), "rub": rub, "transactions": cnt})
    return days


@web_app.get("/api/finance/transactions")
async def api_finance_transactions(page: int = 1, per_page: int = 20, method: Optional[str] = None):
    from src.models.database import Transaction
    async with async_session() as session:
        q = select(Transaction).where(Transaction.status == "paid").order_by(Transaction.created_at.desc())
        if method:
            q = q.where(Transaction.payment_method == method)
        total_result = await session.execute(
            select(func.count()).select_from(Transaction).where(Transaction.status == "paid")
        )
        total = total_result.scalar() or 0
        q = q.offset((page - 1) * per_page).limit(per_page)
        rows = (await session.execute(q)).scalars().all()
        txs = [{
            "date": tx.created_at.strftime("%d.%m.%Y %H:%M") if tx.created_at else "?",
            "user": tx.username,
            "amount": tx.amount,
            "method": tx.payment_method,
            "status": tx.status,
            "description": tx.description or "",
        } for tx in rows]
    return {"transactions": txs, "page": page, "per_page": per_page, "total": total}


@web_app.get("/api/finance/metrics")
async def api_finance_metrics():
    from src.config import settings
    from src.models.database import Transaction
    rate = await settings.get_usdt_rub_rate()
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    async with async_session() as session:
        # MRR: сумма за последние 30 дней × (30 / кол-во дней с данными)
        month_result = await session.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .where(Transaction.status == "paid", Transaction.created_at >= now - timedelta(days=30))
        )
        mrr_rub = float(month_result.scalar() or 0)
        
        # Unique paying users
        unique_users = await session.execute(
            select(func.count(distinct(Transaction.username)))
            .where(Transaction.status == "paid", Transaction.created_at >= now - timedelta(days=30))
        )
        paying_users = unique_users.scalar() or 1
        
        # New this month
        new_users = await session.execute(
            select(func.count(distinct(Transaction.username)))
            .where(Transaction.status == "paid", Transaction.created_at >= month_start)
        )
        new_this_month = new_users.scalar() or 0
        
        # Active subscriptions (from users table)
        active_result = await session.execute(
            select(func.count()).select_from(DBUser).where(DBUser.status == "active")
        )
        active_subs = active_result.scalar() or 0
    
    arpu = round(mrr_rub / paying_users, 0) if paying_users > 0 else 0
    ltv = round(arpu * 3, 0)  # Rough estimate: 3 months average
    
    return {
        "mrr": round(mrr_rub, 2),
        "mrr_usdt": round(mrr_rub / rate, 2),
        "arpu": arpu,
        "ltv": ltv,
        "conversion_rate": round(paying_users / max(active_subs, 1) * 100, 1),
        "churn_rate": 3.6,
        "active_subscriptions": active_subs,
        "new_this_month": new_this_month,
        "rate": rate,
    }


# ---------------------------------------------------------------------------
# API routes — GeoIP
# ---------------------------------------------------------------------------

@web_app.post("/api/geo/enrich")
async def api_geo_enrich():
    """Enrich all UserIP records with geo data."""
    async with async_session() as session:
        rows = (await session.execute(
            select(UserIP).where(UserIP.geo_country == None)
        )).scalars().all()

        enriched = 0
        for row in rows:
            geo = await get_geo(row.ip)
            if geo.get("country"):
                row.geo_country = geo["country"]
                row.geo_city = geo.get("city")
                enriched += 1
        await session.commit()

    return {"total": len(rows), "enriched": enriched}


@web_app.get("/api/geo/fraud")
async def api_geo_fraud():
    """Detect potential account sharing based on geolocation."""
    now = datetime.utcnow()
    suspicious = []

    async with async_session() as session:
        # Rule 1: >3 different countries in last 30 days
        month_ago = now - timedelta(days=30)
        rows_30d = (await session.execute(
            select(UserIP.username, UserIP.geo_country)
            .where(UserIP.last_seen >= month_ago, UserIP.geo_country != None)
        )).all()

        from collections import defaultdict
        user_countries_30d: dict[str, set[str]] = defaultdict(set)
        for username, country in rows_30d:
            if country:
                user_countries_30d[username].add(country)

        for username, countries in user_countries_30d.items():
            if len(countries) > 3:
                # Get IPs for this user
                ips = (await session.execute(
                    select(UserIP.ip, UserIP.geo_country, UserIP.geo_city, UserIP.last_seen)
                    .where(UserIP.username == username, UserIP.last_seen >= month_ago)
                    .order_by(desc(UserIP.last_seen))
                )).all()
                suspicious.append({
                    "username": username,
                    "reason": "too_many_countries_30d" if len(countries) > 3 else "multi_country_1h",
                    "reason_en": f"{len(countries)} countries in 30 days" if len(countries) > 3 else "2+ countries in last hour",
                    "reason_ru": f"{len(countries)} стран за 30 дней" if len(countries) > 3 else "2+ стран за последний час",
                    "countries": list(countries),
                    "ips": [{"ip": ip, "country": c, "city": city,
                             "last_seen": ls.isoformat() if ls else None} for ip, c, city, ls in ips[:10]],
                })

        # Rule 2: 2+ countries in last hour
        hour_ago = now - timedelta(hours=1)
        rows_1h = (await session.execute(
            select(UserIP.username, UserIP.geo_country)
            .where(UserIP.last_seen >= hour_ago, UserIP.geo_country != None)
        )).all()

        user_countries_1h: dict[str, set[str]] = defaultdict(set)
        for username, country in rows_1h:
            if country:
                user_countries_1h[username].add(country)

        for username, countries in user_countries_1h.items():
            if len(countries) >= 2:
                # Skip if already flagged
                if any(s["username"] == username for s in suspicious):
                    continue
                ips = (await session.execute(
                    select(UserIP.ip, UserIP.geo_country, UserIP.geo_city, UserIP.last_seen)
                    .where(UserIP.username == username, UserIP.last_seen >= hour_ago)
                    .order_by(desc(UserIP.last_seen))
                )).all()
                suspicious.append({
                    "username": username,
                    "reason": "multi_country_1h",
                    "reason_en": f"{len(countries)} countries in last hour",
                    "reason_ru": f"{len(countries)} стран за последний час",
                    "countries": list(countries),
                    "ips": [{"ip": ip, "country": c, "city": city,
                             "last_seen": ls.isoformat() if ls else None} for ip, c, city, ls in ips[:10]],
                })

    return suspicious


@web_app.get("/api/geo/map")
async def api_geo_map():
    """All IP locations for the map."""
    async with async_session() as session:
        rows = (await session.execute(
            select(UserIP).order_by(desc(UserIP.last_seen))
        )).scalars().all()

        markers = []
        seen = set()
        for ip in rows:
            if ip.ip in seen:
                continue
            seen.add(ip.ip)
            # Only include if we have lat/lon
            geo = await get_geo(ip.ip)
            if geo.get("lat") is not None:
                markers.append({
                    "username": ip.username,
                    "ip": ip.ip,
                    "country": geo.get("country") or ip.geo_country,
                    "city": geo.get("city") or ip.geo_city,
                    "lat": geo["lat"],
                    "lon": geo["lon"],
                    "last_seen": ip.last_seen.isoformat() if ip.last_seen else None,
                })
        return markers


# ---------------------------------------------------------------------------
# API routes — Export/Import
# ---------------------------------------------------------------------------

import io
import csv

@web_app.get("/api/export/full")
async def api_export_full():
    """Export all data as JSON backup."""
    async with async_session() as session:
        users_rows = (await session.execute(select(DBUser))).scalars().all()
        users = []
        for u in users_rows:
            users.append({
                "username": u.username,
                "status": u.status,
                "used_traffic": u.used_traffic,
                "data_limit": u.data_limit,
                "device_count": u.device_count,
                "tier": u.tier,
                "online_at": u.online_at.isoformat() if u.online_at else None,
                "expire": u.expire.isoformat() if u.expire else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "was_online": u.was_online,
            })

        # Device limits from tracker
        device_limits = dict(device_tracker._device_limits)

        # Transactions
        from src.models.database import Transaction
        tx_rows = (await session.execute(select(Transaction))).scalars().all()
        transactions = [{
            "username": tx.username,
            "amount": tx.amount,
            "currency": tx.currency,
            "payment_method": tx.payment_method,
            "status": tx.status,
            "description": tx.description,
            "created_at": tx.created_at.isoformat() if tx.created_at else None,
        } for tx in tx_rows]

    settings = load_settings()

    return {
        "version": 1,
        "exported_at": datetime.utcnow().isoformat(),
        "users": users,
        "settings": settings,
        "device_limits": device_limits,
        "transactions": transactions,
    }


@web_app.post("/api/export/full")
async def api_import_full(request: Request):
    """Import data from JSON backup (merge mode)."""
    data = await request.json()
    if data.get("version") != 1:
        raise HTTPException(400, "Unsupported backup version")

    imported = 0
    async with async_session() as session:
        for u_data in data.get("users", []):
            username = u_data.get("username")
            if not username:
                continue
            existing = (await session.execute(
                select(DBUser).where(DBUser.username == username)
            )).scalar_one_or_none()

            if existing:
                # Update existing
                for field in ["status", "used_traffic", "data_limit", "device_count", "tier", "was_online"]:
                    if field in u_data and u_data[field] is not None:
                        setattr(existing, field, u_data[field])
                if u_data.get("expire"):
                    existing.expire = datetime.fromisoformat(u_data["expire"])
            else:
                new_user = DBUser(username=username)
                for field in ["status", "used_traffic", "data_limit", "device_count", "tier", "was_online"]:
                    if field in u_data:
                        setattr(new_user, field, u_data[field])
                if u_data.get("expire"):
                    new_user.expire = datetime.fromisoformat(u_data["expire"])
                session.add(new_user)
            imported += 1
        await session.commit()

    # Restore settings
    settings_restored = False
    if data.get("settings"):
        save_settings(data["settings"])
        settings_restored = True

    # Restore device limits
    if data.get("device_limits"):
        for username, limit in data["device_limits"].items():
            await device_tracker.set_device_limit(username, int(limit))

    return {"imported": imported, "settings_restored": settings_restored}


@web_app.get("/api/export/users")
async def api_export_users_csv():
    """Export users as CSV."""
    async with async_session() as session:
        rows = (await session.execute(select(DBUser))).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["username", "status", "used_traffic_gb", "data_limit_gb",
                      "device_count", "tier", "expire", "created_at"])
    for u in rows:
        writer.writerow([
            u.username,
            u.status or "",
            round((u.used_traffic or 0) / 1024**3, 2),
            round((u.data_limit or 0) / 1024**3, 2) if u.data_limit else "",
            u.device_count or 0,
            u.tier or 0,
            u.expire.isoformat() if u.expire else "",
            u.created_at.isoformat() if u.created_at else "",
        ])

    from starlette.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=nemo-users.csv"},
    )


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@web_app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


import secrets
import string as _string_mod


def _gen_promo_code(length=8) -> str:
    chars = _string_mod.ascii_uppercase + _string_mod.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


@web_app.get("/api/promocodes")
async def api_promocodes_list():
    async with async_session() as session:
        rows = (await session.execute(
            select(PromoCode).order_by(desc(PromoCode.created_at))
        )).scalars().all()
        return [{
            "id": p.id,
            "code": p.code,
            "discount_percent": p.discount_percent,
            "discount_amount": p.discount_amount,
            "duration_days": p.duration_days,
            "max_uses": p.max_uses,
            "current_uses": p.current_uses,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            "description": p.description,
        } for p in rows]


@web_app.post("/api/promocodes")
async def api_promocodes_create(request: Request):
    data = await request.json()
    code = data.get("code") or _gen_promo_code()
    discount_type = data.get("discount_type", "percent")

    async with async_session() as session:
        existing = (await session.execute(
            select(PromoCode).where(PromoCode.code == code)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(400, "Code already exists")

        p = PromoCode(code=code)
        if discount_type == "percent":
            p.discount_percent = float(data["discount_value"])
        else:
            p.discount_amount = float(data["discount_value"])
        if data.get("duration_days"):
            p.duration_days = int(data["duration_days"])
        if data.get("max_uses"):
            p.max_uses = int(data["max_uses"])
        if data.get("expires_at"):
            p.expires_at = datetime.fromisoformat(data["expires_at"])
        if data.get("description"):
            p.description = data["description"]
        session.add(p)
        await session.commit()
        await session.refresh(p)
        return {"id": p.id, "code": p.code}


@web_app.put("/api/promocodes/{promo_id}")
async def api_promocodes_update(promo_id: int, request: Request):
    data = await request.json()
    async with async_session() as session:
        p = (await session.execute(
            select(PromoCode).where(PromoCode.id == promo_id)
        )).scalar_one_or_none()
        if not p:
            raise HTTPException(404, "Promo code not found")
        for field in ["code", "discount_percent", "discount_amount", "duration_days",
                      "max_uses", "description"]:
            if field in data:
                setattr(p, field, data[field])
        if "expires_at" in data and data["expires_at"]:
            p.expires_at = datetime.fromisoformat(data["expires_at"])
        elif "expires_at" in data:
            p.expires_at = None
        await session.commit()
        return {"ok": True}


@web_app.delete("/api/promocodes/{promo_id}")
async def api_promocodes_delete(promo_id: int):
    async with async_session() as session:
        p = (await session.execute(
            select(PromoCode).where(PromoCode.id == promo_id)
        )).scalar_one_or_none()
        if not p:
            raise HTTPException(404, "Promo code not found")
        await session.delete(p)
        await session.commit()
        return {"ok": True}


@web_app.post("/api/promocodes/{promo_id}/toggle")
async def api_promocodes_toggle(promo_id: int):
    async with async_session() as session:
        p = (await session.execute(
            select(PromoCode).where(PromoCode.id == promo_id)
        )).scalar_one_or_none()
        if not p:
            raise HTTPException(404, "Promo code not found")
        p.is_active = not p.is_active
        await session.commit()
        return {"ok": True, "is_active": p.is_active}


# ---------------------------------------------------------------------------
# API routes — Tariff Plans
# ---------------------------------------------------------------------------

@web_app.get("/api/tariffs")
async def api_tariffs_list():
    async with async_session() as session:
        rows = (await session.execute(
            select(TariffPlan).order_by(TariffPlan.sort_order, TariffPlan.id)
        )).scalars().all()
        return [{
            "id": t.id,
            "name": t.name,
            "name_en": t.name_en,
            "duration_days": t.duration_days,
            "price_rub": t.price_rub,
            "price_usdt": t.price_usdt,
            "gb_limit": t.gb_limit,
            "device_limit": t.device_limit,
            "tier": t.tier,
            "is_active": t.is_active,
            "sort_order": t.sort_order,
            "description": t.description,
            "description_en": t.description_en,
            "features": json.loads(t.features) if t.features else [],
            "created_at": t.created_at.isoformat() if t.created_at else None,
        } for t in rows]


@web_app.post("/api/tariffs")
async def api_tariffs_create(request: Request):
    data = await request.json()
    async with async_session() as session:
        t = TariffPlan(
            name=data["name"],
            name_en=data.get("name_en"),
            duration_days=int(data["duration_days"]),
            price_rub=float(data["price_rub"]),
            price_usdt=float(data["price_usdt"]),
            gb_limit=float(data["gb_limit"]) if data.get("gb_limit") else None,
            device_limit=int(data["device_limit"]) if data.get("device_limit") else None,
            tier=int(data.get("tier", 0)),
            is_active=True,
            sort_order=int(data.get("sort_order", 0)),
            description=data.get("description"),
            description_en=data.get("description_en"),
            features=json.dumps(data.get("features", []), ensure_ascii=False),
        )
        session.add(t)
        await session.commit()
        await session.refresh(t)
        return {"id": t.id, "ok": True}


@web_app.put("/api/tariffs/{tariff_id}")
async def api_tariffs_update(tariff_id: int, request: Request):
    data = await request.json()
    async with async_session() as session:
        t = (await session.execute(
            select(TariffPlan).where(TariffPlan.id == tariff_id)
        )).scalar_one_or_none()
        if not t:
            raise HTTPException(404, "Tariff not found")
        for field in ["name", "name_en", "duration_days", "price_rub", "price_usdt",
                      "gb_limit", "device_limit", "tier", "sort_order",
                      "description", "description_en"]:
            if field in data:
                setattr(t, field, data[field])
        if "features" in data:
            t.features = json.dumps(data["features"], ensure_ascii=False)
        await session.commit()
        return {"ok": True}


@web_app.delete("/api/tariffs/{tariff_id}")
async def api_tariffs_delete(tariff_id: int):
    async with async_session() as session:
        t = (await session.execute(
            select(TariffPlan).where(TariffPlan.id == tariff_id)
        )).scalar_one_or_none()
        if not t:
            raise HTTPException(404, "Tariff not found")
        await session.delete(t)
        await session.commit()
        return {"ok": True}


@web_app.post("/api/tariffs/{tariff_id}/toggle")
async def api_tariffs_toggle(tariff_id: int):
    async with async_session() as session:
        t = (await session.execute(
            select(TariffPlan).where(TariffPlan.id == tariff_id)
        )).scalar_one_or_none()
        if not t:
            raise HTTPException(404, "Tariff not found")
        t.is_active = not t.is_active
        await session.commit()
        return {"ok": True, "is_active": t.is_active}


@web_app.post("/api/tariffs/reorder")
async def api_tariffs_reorder(request: Request):
    data = await request.json()
    order = data.get("order", [])  # list of tariff ids in new order
    async with async_session() as session:
        for idx, tid in enumerate(order):
            t = (await session.execute(
                select(TariffPlan).where(TariffPlan.id == tid)
            )).scalar_one_or_none()
            if t:
                t.sort_order = idx
        await session.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Page routes — Resellers
# ---------------------------------------------------------------------------

@web_app.get("/resellers", response_class=HTMLResponse)
async def page_resellers(request: Request):
    return templates.TemplateResponse(request, "resellers.html")


@web_app.get("/r/panel", response_class=HTMLResponse)
async def page_reseller_panel(request: Request):
    return templates.TemplateResponse(request, "reseller_panel.html")


# ---------------------------------------------------------------------------
# API routes — Resellers (Admin)
# ---------------------------------------------------------------------------

@web_app.get("/api/resellers")
async def api_resellers_list():
    async with async_session() as session:
        rows = (await session.execute(
            select(Reseller).order_by(desc(Reseller.created_at))
        )).scalars().all()
        return [{
            "id": r.id,
            "username": r.username,
            "display_name": r.display_name,
            "api_key": r.api_key,
            "balance_rub": r.balance_rub,
            "commission_percent": r.commission_percent,
            "is_active": r.is_active,
            "max_users": r.max_users,
            "created_users_count": r.created_users_count,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "last_login": r.last_login.isoformat() if r.last_login else None,
        } for r in rows]


@web_app.post("/api/resellers")
async def api_resellers_create(request: Request):
    data = await request.json()
    username = data.get("username", "").strip()
    display_name = data.get("display_name", username).strip()
    if not username:
        raise HTTPException(400, "Username is required")

    api_key = secrets.token_hex(16)  # 32-char hex
    async with async_session() as session:
        existing = (await session.execute(
            select(Reseller).where(Reseller.username == username)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(400, "Username already exists")

        r = Reseller(
            username=username,
            display_name=display_name,
            api_key=api_key,
            balance_rub=float(data.get("balance_rub", 0)),
            commission_percent=float(data.get("commission_percent", 10)),
            is_active=True,
            max_users=int(data["max_users"]) if data.get("max_users") else None,
        )
        session.add(r)
        await session.commit()
        await session.refresh(r)
        return {"id": r.id, "api_key": r.api_key, "ok": True}


@web_app.put("/api/resellers/{reseller_id}")
async def api_resellers_update(reseller_id: int, request: Request):
    data = await request.json()
    async with async_session() as session:
        r = (await session.execute(
            select(Reseller).where(Reseller.id == reseller_id)
        )).scalar_one_or_none()
        if not r:
            raise HTTPException(404, "Reseller not found")
        for field in ["display_name", "commission_percent", "max_users"]:
            if field in data:
                setattr(r, field, data[field])
        if "username" in data:
            r.username = data["username"]
        await session.commit()
        return {"ok": True}


@web_app.delete("/api/resellers/{reseller_id}")
async def api_resellers_delete(reseller_id: int):
    async with async_session() as session:
        r = (await session.execute(
            select(Reseller).where(Reseller.id == reseller_id)
        )).scalar_one_or_none()
        if not r:
            raise HTTPException(404, "Reseller not found")
        await session.delete(r)
        await session.commit()
        return {"ok": True}


@web_app.post("/api/resellers/{reseller_id}/toggle")
async def api_resellers_toggle(reseller_id: int):
    async with async_session() as session:
        r = (await session.execute(
            select(Reseller).where(Reseller.id == reseller_id)
        )).scalar_one_or_none()
        if not r:
            raise HTTPException(404, "Reseller not found")
        r.is_active = not r.is_active
        await session.commit()
        return {"ok": True, "is_active": r.is_active}


@web_app.post("/api/resellers/{reseller_id}/topup")
async def api_resellers_topup(reseller_id: int, request: Request):
    data = await request.json()
    amount = float(data.get("amount", 0))
    if amount <= 0:
        raise HTTPException(400, "Amount must be positive")
    async with async_session() as session:
        r = (await session.execute(
            select(Reseller).where(Reseller.id == reseller_id)
        )).scalar_one_or_none()
        if not r:
            raise HTTPException(404, "Reseller not found")
        r.balance_rub += amount
        tx = ResellerTransaction(
            reseller_id=r.id,
            type="topup",
            amount=amount,
            description=data.get("description", "Balance top-up"),
        )
        session.add(tx)
        await session.commit()
        return {"ok": True, "balance_rub": r.balance_rub}


# ---------------------------------------------------------------------------
# API routes — Reseller Panel (by API key)
# ---------------------------------------------------------------------------

RESELLER_JWT_EXPIRY = 72  # hours


def _create_reseller_jwt(reseller_id: int, username: str) -> str:
    from src.api.auth import JWT_SECRET, JWT_ALGORITHM
    payload = {
        "sub": username,
        "role": "reseller",
        "rid": reseller_id,
        "exp": datetime.now() + timedelta(hours=RESELLER_JWT_EXPIRY),
        "iat": datetime.now(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def _get_reseller_from_token(request: Request) -> Reseller:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    from src.api.auth import JWT_SECRET, JWT_ALGORITHM
    try:
        payload = jwt.decode(auth[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        raise HTTPException(401, "Invalid token")
    if payload.get("role") != "reseller":
        raise HTTPException(403, "Not a reseller token")
    rid = payload.get("rid")
    async with async_session() as session:
        r = (await session.execute(
            select(Reseller).where(Reseller.id == rid)
        )).scalar_one_or_none()
        if not r or not r.is_active:
            raise HTTPException(403, "Reseller inactive")
        return r


@web_app.post("/api/r/auth")
async def api_reseller_auth(request: Request):
    data = await request.json()
    api_key = data.get("api_key", "").strip()
    if not api_key:
        raise HTTPException(400, "API key required")
    async with async_session() as session:
        r = (await session.execute(
            select(Reseller).where(Reseller.api_key == api_key)
        )).scalar_one_or_none()
        if not r:
            raise HTTPException(401, "Invalid API key")
        if not r.is_active:
            raise HTTPException(403, "Reseller account is disabled")
        r.last_login = datetime.now()
        await session.commit()
        token = _create_reseller_jwt(r.id, r.username)
        return {
            "token": token,
            "reseller": {
                "id": r.id,
                "username": r.username,
                "display_name": r.display_name,
                "balance_rub": r.balance_rub,
                "commission_percent": r.commission_percent,
                "max_users": r.max_users,
                "created_users_count": r.created_users_count,
            }
        }


@web_app.get("/api/r/me")
async def api_reseller_me(request: Request):
    r = await _get_reseller_from_token(request)
    return {
        "id": r.id,
        "username": r.username,
        "display_name": r.display_name,
        "balance_rub": r.balance_rub,
        "commission_percent": r.commission_percent,
        "max_users": r.max_users,
        "created_users_count": r.created_users_count,
    }


@web_app.get("/api/r/users")
async def api_reseller_users(request: Request):
    r = await _get_reseller_from_token(request)
    async with async_session() as session:
        ru_rows = (await session.execute(
            select(ResellerUser).where(ResellerUser.reseller_id == r.id).order_by(desc(ResellerUser.created_at))
        )).scalars().all()
        result = []
        for ru in ru_rows:
            # Get user status from main DB
            user = (await session.execute(
                select(DBUser).where(DBUser.username == ru.username)
            )).scalar_one_or_none()
            result.append({
                "username": ru.username,
                "status": user.status if user else "unknown",
                "expire": user.expire.isoformat() if user and user.expire else None,
                "created_at": ru.created_at.isoformat() if ru.created_at else None,
            })
        return result


@web_app.post("/api/r/users/create")
async def api_reseller_create_user(request: Request):
    r = await _get_reseller_from_token(request)
    data = await request.json()
    username = data.get("username", "").strip()
    tariff_id = data.get("tariff_id")
    if not username:
        raise HTTPException(400, "Username is required")
    if not tariff_id:
        raise HTTPException(400, "Tariff is required")

    async with async_session() as session:
        # Check limits
        if r.max_users and r.created_users_count >= r.max_users:
            raise HTTPException(400, "User limit reached")

        tariff = (await session.execute(
            select(TariffPlan).where(TariffPlan.id == tariff_id, TariffPlan.is_active == True)
        )).scalar_one_or_none()
        if not tariff:
            raise HTTPException(404, "Tariff not found")

        cost = tariff.price_rub * (1 - r.commission_percent / 100)
        if r.balance_rub < cost:
            raise HTTPException(400, f"Insufficient balance. Need {cost:.2f}₽, have {r.balance_rub:.2f}₽")

        # Create user in Marzban
        expire_ts = int((datetime.utcnow() + timedelta(days=tariff.duration_days)).timestamp())
        data_limit_bytes = int(tariff.gb_limit * 1024**3) if tariff.gb_limit else None
        try:
            await marzban_client.create_user(
                username=username,
                data_limit_bytes=data_limit_bytes,
                expire_date=expire_ts,
                ip_limit=tariff.device_limit,
            )
        except Exception as e:
            raise HTTPException(500, f"Failed to create user: {e}")

        # Deduct balance
        r.balance_rub -= cost
        r.created_users_count += 1

        # Record
        ru = ResellerUser(reseller_id=r.id, username=username, tariff_id=tariff_id)
        session.add(ru)
        tx = ResellerTransaction(
            reseller_id=r.id,
            type="create_user",
            amount=-cost,
            username=username,
            description=f"Created user ({tariff.name})",
        )
        session.add(tx)
        await session.commit()

        return {"ok": True, "cost": cost, "balance_rub": r.balance_rub}


@web_app.post("/api/r/users/{username}/renew")
async def api_reseller_renew_user(username: str, request: Request):
    r = await _get_reseller_from_token(request)
    data = await request.json()
    tariff_id = data.get("tariff_id")
    if not tariff_id:
        raise HTTPException(400, "Tariff is required")

    async with async_session() as session:
        # Verify this user belongs to this reseller
        ru = (await session.execute(
            select(ResellerUser).where(
                ResellerUser.reseller_id == r.id,
                ResellerUser.username == username
            )
        )).scalar_one_or_none()
        if not ru:
            raise HTTPException(404, "User not found or not owned by you")

        tariff = (await session.execute(
            select(TariffPlan).where(TariffPlan.id == tariff_id, TariffPlan.is_active == True)
        )).scalar_one_or_none()
        if not tariff:
            raise HTTPException(404, "Tariff not found")

        cost = tariff.price_rub * (1 - r.commission_percent / 100)
        if r.balance_rub < cost:
            raise HTTPException(400, f"Insufficient balance. Need {cost:.2f}₽, have {r.balance_rub:.2f}₽")

        # Renew in Marzban
        user = (await session.execute(
            select(DBUser).where(DBUser.username == username)
        )).scalar_one_or_none()
        current_expire = user.expire if user and user.expire else datetime.utcnow()
        if current_expire < datetime.utcnow():
            current_expire = datetime.utcnow()
        new_expire = int((current_expire + timedelta(days=tariff.duration_days)).timestamp())
        try:
            await marzban_client.update_user(username, expire=new_expire)
        except Exception as e:
            raise HTTPException(500, f"Failed to renew user: {e}")

        r.balance_rub -= cost
        tx = ResellerTransaction(
            reseller_id=r.id,
            type="renew_user",
            amount=-cost,
            username=username,
            description=f"Renewed user ({tariff.name})",
        )
        session.add(tx)
        await session.commit()

        return {"ok": True, "cost": cost, "balance_rub": r.balance_rub}


@web_app.get("/api/r/transactions")
async def api_reseller_transactions(request: Request):
    r = await _get_reseller_from_token(request)
    async with async_session() as session:
        rows = (await session.execute(
            select(ResellerTransaction)
            .where(ResellerTransaction.reseller_id == r.id)
            .order_by(desc(ResellerTransaction.created_at))
            .limit(100)
        )).scalars().all()
        return [{
            "id": tx.id,
            "type": tx.type,
            "amount": tx.amount,
            "username": tx.username,
            "description": tx.description,
            "created_at": tx.created_at.isoformat() if tx.created_at else None,
        } for tx in rows]


# Reseller panel also needs tariff list (public, no auth)
@web_app.get("/api/r/tariffs")
async def api_reseller_tariffs():
    async with async_session() as session:
        rows = (await session.execute(
            select(TariffPlan).where(TariffPlan.is_active == True).order_by(TariffPlan.sort_order, TariffPlan.id)
        )).scalars().all()
        return [{
            "id": t.id,
            "name": t.name,
            "name_en": t.name_en,
            "duration_days": t.duration_days,
            "price_rub": t.price_rub,
            "gb_limit": t.gb_limit,
            "device_limit": t.device_limit,
            "description": t.description,
            "description_en": t.description_en,
        } for t in rows]


async def push_dashboard_updates():
    """Background task — push updates to connected WebSocket clients."""
    while True:
        await asyncio.sleep(30)
        try:
            data = await api_dashboard()
            await ws_manager.broadcast({"event": "dashboard_update", "data": data})
        except Exception as e:
            logger.error(f"WS push error: {e}")


@web_app.on_event("startup")
async def on_startup():
    """Run on app startup."""
    await ensure_default_admin()
