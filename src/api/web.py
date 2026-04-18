"""
Nemo Tracker — Web Admin Panel (FastAPI)
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ---------------------------------------------------------------------------
# App init
# ---------------------------------------------------------------------------

web_app = FastAPI(title="Nemo Tracker", docs_url=None, redoc_url=None)

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

web_app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))

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
# Helpers – load / save settings  (simple JSON file)
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
# Mock data helpers (replace with real Marzban / DB calls later)
# ---------------------------------------------------------------------------

def _mock_dashboard():
    now = datetime.utcnow()
    online_24h = [{"hour": (now - timedelta(hours=23 - i)).strftime("%H:00"),
                   "count": 10 + int(20 * abs((i % 7 - 3) / 3))} for i in range(24)]
    traffic_30d = [{"day": (now - timedelta(days=29 - i)).strftime("%b %d"),
                    "value": round(5 + 15 * abs((i % 11 - 5) / 5), 1)} for i in range(30)]
    growth = [{"month": (now - timedelta(days=30 * (5 - i))).strftime("%b"),
               "users": 50 + i * 30 + (i * i)} for i in range(6)]
    peak_hours = {"labels": ["00-04", "04-08", "08-12", "12-16", "16-20", "20-24"],
                  "values": [5, 3, 15, 20, 25, 18]}
    return {
        "stats": {"total_users": 234, "active_users": 187, "online_now": 42,
                  "total_traffic": "3.2 TB"},
        "online_24h": online_24h,
        "traffic_30d": traffic_30d,
        "growth": growth,
        "peak_hours": peak_hours,
        "recent_alerts": [
            {"type": "device_over", "message": "User alex has 6 devices (limit: 3)", "time": "2 min ago"},
            {"type": "traffic_80", "message": "User maria used 85% of traffic", "time": "15 min ago"},
            {"type": "new_user", "message": "New user registered: john", "time": "1 hr ago"},
        ]
    }

def _mock_users():
    statuses = ["active", "active", "active", "disabled", "active", "expired", "active"]
    users = []
    names = ["alex", "maria", "john", "olga", "dmitry", "anna", "sergey", "kate",
             "peter", "elena", "ivan", "nina"]
    for i, n in enumerate(names):
        used = round(1 + 80 * ((i * 37) % 100) / 100, 1)
        limit = 100.0
        users.append({
            "username": n,
            "status": statuses[i % len(statuses)],
            "traffic_used": used,
            "traffic_limit": limit,
            "devices": (i * 3) % 7,
            "last_online": (datetime.utcnow() - timedelta(hours=(i * 5) % 48)).isoformat(),
            "expire": (datetime.utcnow() + timedelta(days=30 - i * 2)).strftime("%Y-%m-%d"),
        })
    return users

def _mock_user_detail(username: str):
    return {
        "username": username,
        "status": "active",
        "traffic_used": 45.2,
        "traffic_limit": 100.0,
        "devices": 3,
        "device_limit": 5,
        "created": "2025-10-15",
        "expire": "2026-10-15",
        "traffic_7d": [{"day": (datetime.utcnow() - timedelta(days=6 - i)).strftime("%b %d"),
                         "dl": round(2 + 8 * abs((i % 5 - 2) / 2), 1),
                         "ul": round(0.5 + 2 * abs((i % 3) / 2), 1)} for i in range(7)],
        "ip_history": [
            {"ip": "185.220.101.34", "country": "DE", "city": "Berlin", "first": "2026-04-10 08:23",
             "last": "2026-04-18 09:01"},
            {"ip": "91.108.56.12", "country": "RU", "city": "Moscow", "first": "2026-04-12 14:00",
             "last": "2026-04-17 22:45"},
        ],
        "connections": [
            {"time": "2026-04-18 09:01", "ip": "185.220.101.34", "device": "iPhone"},
            {"time": "2026-04-18 08:30", "ip": "91.108.56.12", "device": "MacBook"},
        ],
    }

def _mock_devices():
    rows = []
    names = ["alex", "maria", "john", "olga", "dmitry", "anna", "sergey"]
    for i, n in enumerate(names):
        ips = 1 + (i * 2) % 6
        limit = 3 + i % 3
        status = "ok" if ips <= limit else ("warning" if ips == limit else "over")
        rows.append({"username": n, "unique_ips": ips, "device_limit": limit, "status": status})
    return rows

def _mock_device_detail(username: str):
    return {
        "username": username,
        "device_limit": 5,
        "ips": [
            {"ip": "185.220.101.34", "country": "🇩🇪 Germany", "city": "Berlin",
             "first_seen": "2026-04-10 08:23", "last_seen": "2026-04-18 09:01"},
            {"ip": "91.108.56.12", "country": "🇷🇺 Russia", "city": "Moscow",
             "first_seen": "2026-04-12 14:00", "last_seen": "2026-04-17 22:45"},
            {"ip": "104.244.72.7", "country": "🇳🇱 Netherlands", "city": "Amsterdam",
             "first_seen": "2026-04-15 11:30", "last_seen": "2026-04-16 19:20"},
            {"ip": "45.133.1.55", "country": "🇫🇮 Finland", "city": "Helsinki",
             "first_seen": "2026-04-16 03:00", "last_seen": "2026-04-16 03:05"},
        ]
    }

def _mock_alerts():
    types = ["new_user", "traffic_80", "device_over", "expiring"]
    return [
        {"id": i, "type": types[i % 4],
         "message": f"Alert #{i}: sample message for {types[i%4]}",
         "time": (datetime.utcnow() - timedelta(hours=i * 2)).isoformat(),
         "resolved": i > 5}
        for i in range(12)
    ]

# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@web_app.get("/", response_class=HTMLResponse)
async def page_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@web_app.get("/users", response_class=HTMLResponse)
async def page_users(request: Request):
    return templates.TemplateResponse("users.html", {"request": request})

@web_app.get("/users/{username}", response_class=HTMLResponse)
async def page_user_detail(request: Request, username: str):
    return templates.TemplateResponse("user_detail.html", {"request": request, "username": username})

@web_app.get("/devices", response_class=HTMLResponse)
async def page_devices(request: Request):
    return templates.TemplateResponse("devices.html", {"request": request})

@web_app.get("/devices/{username}", response_class=HTMLResponse)
async def page_device_detail(request: Request, username: str):
    # Reuse user_detail template with device focus — or we can inline in devices.html via JS
    return templates.TemplateResponse("user_detail.html", {"request": request, "username": username, "tab": "devices"})

@web_app.get("/settings", response_class=HTMLResponse)
async def page_settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

@web_app.get("/alerts", response_class=HTMLResponse)
async def page_alerts(request: Request):
    return templates.TemplateResponse("alerts.html", {"request": request})

# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@web_app.get("/api/dashboard")
async def api_dashboard():
    return _mock_dashboard()

@web_app.get("/api/users")
async def api_users():
    return _mock_users()

@web_app.get("/api/users/{username}")
async def api_user_detail(username: str):
    return _mock_user_detail(username)

@web_app.get("/api/devices")
async def api_devices():
    return _mock_devices()

@web_app.get("/api/devices/{username}")
async def api_device_detail(username: str):
    return _mock_device_detail(username)

@web_app.get("/api/alerts")
async def api_alerts(type: Optional[str] = None, resolved: Optional[bool] = None):
    alerts = _mock_alerts()
    if type:
        alerts = [a for a in alerts if a["type"] == type]
    if resolved is not None:
        alerts = [a for a in alerts if a["resolved"] == resolved]
    return alerts

@web_app.post("/api/alerts/{alert_id}/resolve")
async def api_resolve_alert(alert_id: int):
    return {"ok": True}

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
    # TODO: real connection test
    await asyncio.sleep(0.5)
    return {"ok": True, "message": "Connected successfully"}

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
            # Keep alive — client pings or we push periodically
            data = await ws.receive_text()
            # ignore incoming for now
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)

# ---------------------------------------------------------------------------
# Periodic push (call from main app startup)
# ---------------------------------------------------------------------------

async def push_dashboard_updates():
    """Call this from the main app's background loop."""
    while True:
        await asyncio.sleep(10)
        await ws_manager.broadcast({"event": "dashboard_update", "data": _mock_dashboard()})
