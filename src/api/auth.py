"""Nemo Tracker — Authentication & 2FA (TOTP)."""

import base64
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import pyotp
from jose import jwt, JWTError
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from loguru import logger

from pathlib import Path
from src.config import settings
from src.models import async_session
from src.models.database import AdminUser
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))

router = APIRouter()

JWT_SECRET = settings.web_secret_key or "change-this"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
COOKIE_NAME = "nemo_token"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_jwt(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


async def ensure_default_admin():
    """Create default admin from config if no admins exist."""
    async with async_session() as session:
        count = await session.scalar(
            select(func.count()).select_from(AdminUser)
        )
        if count == 0:
            default_user = settings.__dict__.get("admin_username", "admin") or "admin"
            default_pass = settings.__dict__.get("admin_password", "admin") or "admin"
            admin = AdminUser(
                username=default_user,
                password_hash=hash_password(default_pass),
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            logger.info(f"Created default admin user: {default_user}")


# ---------------------------------------------------------------------------
# Auth middleware dependency
# ---------------------------------------------------------------------------

# Paths that don't require auth
PUBLIC_PATHS = {"/login", "/api/auth/login", "/static"}
PUBLIC_PREFIXES = ("/static/",)


async def auth_middleware(request: Request, call_next):
    """Check JWT cookie on all routes except public ones."""
    path = request.url.path

    # Allow public paths
    if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
        return await call_next(request)

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return _redirect_login(request)

    payload = decode_jwt(token)
    if not payload:
        response = _redirect_login(request)
        response.delete_cookie(COOKIE_NAME)
        return response

    # Check user still active
    username = payload.get("sub")
    if username:
        async with async_session() as session:
            admin = await session.scalar(
                select(AdminUser).where(AdminUser.username == username)
            )
            if not admin or not admin.is_active:
                response = _redirect_login(request)
                response.delete_cookie(COOKIE_NAME)
                return response

    request.state.user = username
    return await call_next(request)


def _redirect_login(request: Request):
    """Redirect to login page (HTML) or return 401 (API)."""
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/login")


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@router.get("/login", response_class=HTMLResponse)
async def page_login(request: Request):
    # If already logged in, redirect to dashboard
    token = request.cookies.get(COOKIE_NAME)
    if token and decode_jwt(token):
        from starlette.responses import RedirectResponse
        return RedirectResponse(url="/")
    return templates.TemplateResponse(request, "login.html")


# ---------------------------------------------------------------------------
# API routes — Auth
# ---------------------------------------------------------------------------

@router.post("/api/auth/login")
async def api_login(request: Request):
    data = await request.json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    totp_code = data.get("totp_code")

    if not username or not password:
        raise HTTPException(400, "Username and password required")

    async with async_session() as session:
        admin = await session.scalar(
            select(AdminUser).where(AdminUser.username == username)
        )

        if not admin or not admin.is_active or not verify_password(password, admin.password_hash):
            raise HTTPException(401, "Invalid credentials")

        # Check 2FA
        if admin.totp_secret:
            if not totp_code:
                return JSONResponse({"require_2fa": True, "error": "2FA code required"}, status_code=200)
            totp = pyotp.TOTP(admin.totp_secret)
            if not totp.verify(totp_code, valid_window=1):
                raise HTTPException(401, "Invalid 2FA code")

        # Update last login
        admin.last_login = datetime.now(timezone.utc)
        await session.commit()

    token = create_jwt(username)
    response = JSONResponse({"ok": True, "username": username})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=JWT_EXPIRY_HOURS * 3600,
        samesite="lax",
    )
    return response


@router.post("/api/auth/logout")
async def api_logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE_NAME)
    return response


# ---------------------------------------------------------------------------
# API routes — 2FA
# ---------------------------------------------------------------------------

@router.post("/api/auth/2fa/setup")
async def api_2fa_setup(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(401, "Not authenticated")

    async with async_session() as session:
        admin = await session.scalar(
            select(AdminUser).where(AdminUser.username == user)
        )
        if not admin:
            raise HTTPException(404, "User not found")

        # Generate new TOTP secret
        secret = pyotp.random_base32()
        admin.totp_secret = secret
        await session.commit()

    # Build provisioning URI and QR code
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user, issuer_name="Nemo Tracker")

    # Generate QR as base64 PNG
    import qrcode
    from io import BytesIO
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "secret": secret,
        "qr": f"data:image/png;base64,{qr_b64}",
        "uri": uri,
    }


@router.post("/api/auth/2fa/verify")
async def api_2fa_verify(request: Request):
    """Verify TOTP code and confirm 2FA activation."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(401, "Not authenticated")

    data = await request.json()
    code = data.get("code")

    if not code:
        raise HTTPException(400, "Code required")

    async with async_session() as session:
        admin = await session.scalar(
            select(AdminUser).where(AdminUser.username == user)
        )
        if not admin or not admin.totp_secret:
            raise HTTPException(400, "2FA not set up")

        totp = pyotp.TOTP(admin.totp_secret)
        if not totp.verify(code, valid_window=1):
            raise HTTPException(400, "Invalid code")

    return {"ok": True, "message": "2FA enabled"}


@router.post("/api/auth/2fa/disable")
async def api_2fa_disable(request: Request):
    """Disable 2FA (requires current password)."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(401, "Not authenticated")

    data = await request.json()
    password = data.get("password")

    if not password:
        raise HTTPException(400, "Password required")

    async with async_session() as session:
        admin = await session.scalar(
            select(AdminUser).where(AdminUser.username == user)
        )
        if not admin:
            raise HTTPException(404, "User not found")

        if not verify_password(password, admin.password_hash):
            raise HTTPException(401, "Invalid password")

        admin.totp_secret = None
        await session.commit()

    return {"ok": True, "message": "2FA disabled"}


@router.get("/api/auth/2fa/status")
async def api_2fa_status(request: Request):
    """Get current 2FA status."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(401, "Not authenticated")

    async with async_session() as session:
        admin = await session.scalar(
            select(AdminUser).where(AdminUser.username == user)
        )
        if not admin:
            raise HTTPException(404, "User not found")

        return {
            "enabled": admin.totp_secret is not None,
            "username": admin.username,
            "last_login": admin.last_login.isoformat() if admin.last_login else None,
        }


@router.post("/api/auth/password")
async def api_change_password(request: Request):
    """Change admin password."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(401, "Not authenticated")

    data = await request.json()
    current = data.get("current_password")
    new = data.get("new_password")

    if not current or not new:
        raise HTTPException(400, "Current and new password required")

    if len(new) < 4:
        raise HTTPException(400, "Password too short (min 4 chars)")

    async with async_session() as session:
        admin = await session.scalar(
            select(AdminUser).where(AdminUser.username == user)
        )
        if not admin:
            raise HTTPException(404, "User not found")

        if not verify_password(current, admin.password_hash):
            raise HTTPException(401, "Invalid current password")

        admin.password_hash = hash_password(new)
        await session.commit()

    return {"ok": True, "message": "Password changed"}


# Need this import for ensure_default_admin
from sqlalchemy import func
