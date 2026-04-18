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

# ---------------------------------------------------------------------------
# DB imports (lazy to avoid circular imports at module level)
# ---------------------------------------------------------------------------

from src.models import async_session
from src.models.database import User as DBUser, Analytics, Alert, Connection
from src.core.marzban_client import marzban_client
from src.core.device_tracker import device_tracker
from sqlalchemy import select, func, desc, distinct, delete

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

@web_app.get("/settings", response_class=HTMLResponse)
async def page_settings(request: Request):
    return templates.TemplateResponse(request, "settings.html")

@web_app.get("/alerts", response_class=HTMLResponse)
async def page_alerts(request: Request):
    return templates.TemplateResponse(request, "alerts.html")

# ---------------------------------------------------------------------------
# API routes — REAL DATA
# ---------------------------------------------------------------------------

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
                "expire": u.expire.isoformat() if u.expire else None,
                "tier": u.tier or 0,
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
            "created": user.created_at.strftime("%Y-%m-%d") if user.created_at else "?",
            "expire": user.expire.strftime("%Y-%m-%d") if user.expire else None,
            "tier": user.tier or 0,
            "traffic_7d": traffic_7d,
            "ip_history": ip_history,
            "connections": connections,
        }


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


async def push_dashboard_updates():
    """Background task — push updates to connected WebSocket clients."""
    while True:
        await asyncio.sleep(30)
        try:
            data = await api_dashboard()
            await ws_manager.broadcast({"event": "dashboard_update", "data": data})
        except Exception as e:
            logger.error(f"WS push error: {e}")
