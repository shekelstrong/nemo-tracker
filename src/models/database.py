"""Nemo Tracker — Database models (SQLAlchemy 2.0 async)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, Integer, String, Text, BigInteger, Date, Index, JSON
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class User(Base):
    """Кэш пользователей из Marzban."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active")  # active, disabled, expired, limited
    used_traffic: Mapped[int] = mapped_column(BigInteger, default=0)  # bytes
    data_limit: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # bytes
    online_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expire: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tier: Mapped[int] = mapped_column(Integer, default=0)
    device_count: Mapped[int] = mapped_column(Integer, default=0)
    gb_limit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_synced: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Флаг: был ли онлайн при предыдущей синхронизации
    was_online: Mapped[bool] = mapped_column(Boolean, default=False)

    def traffic_usage_percent(self) -> Optional[float]:
        if self.data_limit and self.data_limit > 0:
            return (self.used_traffic / self.data_limit) * 100
        return None


class Connection(Base):
    """История подключений/отключений."""
    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    online_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    offline_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    node_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)


class UserIP(Base):
    """Уникальные IP пользователей — для device tracking."""
    __tablename__ = "user_ips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    ip: Mapped[str] = mapped_column(String(45), nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source: Mapped[str] = mapped_column(String(16), default="sub")  # 'sub' or 'xray'
    geo_country: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    geo_city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    __table_args__ = (
        Index('ix_user_ips_username_ip', 'username', 'ip', unique=True),
    )


class Analytics(Base):
    """Агрегированная статистика за день."""
    __tablename__ = "analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(Date, unique=True, nullable=False, index=True)
    total_users: Mapped[int] = mapped_column(Integer, default=0)
    active_users: Mapped[int] = mapped_column(Integer, default=0)
    online_users: Mapped[int] = mapped_column(Integer, default=0)
    total_traffic_gb: Mapped[float] = mapped_column(Float, default=0.0)
    new_users: Mapped[int] = mapped_column(Integer, default=0)
    expired_users: Mapped[int] = mapped_column(Integer, default=0)


class Transaction(Base):
    """Финансовые транзакции."""
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="RUB")  # RUB / USDT
    payment_method: Mapped[str] = mapped_column(String(32), default="cryptopay")  # cryptopay / platega
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending / paid / failed
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DailyRevenue(Base):
    """Агрегированная выручка за день."""
    __tablename__ = "daily_revenue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(Date, unique=True, nullable=False, index=True)
    total_rub: Mapped[float] = mapped_column(Float, default=0.0)
    total_usdt: Mapped[float] = mapped_column(Float, default=0.0)
    transaction_count: Mapped[int] = mapped_column(Integer, default=0)
    new_subscriptions: Mapped[int] = mapped_column(Integer, default=0)
    renewals: Mapped[int] = mapped_column(Integer, default=0)


class AdminUser(Base):
    """Администраторы панели."""
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    totp_secret: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PromoCode(Base):
    """Промокоды для скидок."""
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    discount_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    discount_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duration_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_uses: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class TariffPlan(Base):
    """Тарифные планы."""
    __tablename__ = "tariff_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    price_rub: Mapped[float] = mapped_column(Float, nullable=False)
    price_usdt: Mapped[float] = mapped_column(Float, nullable=False)
    gb_limit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # null = безлимит
    device_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # null = безлимит
    tier: Mapped[int] = mapped_column(Integer, default=0)  # 0=standard, 1=premium
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    features: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Reseller(Base):
    """Реселлеры."""
    __tablename__ = "resellers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    api_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    balance_rub: Mapped[float] = mapped_column(Float, default=0.0)
    commission_percent: Mapped[float] = mapped_column(Float, default=10.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_users: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_users_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ResellerTransaction(Base):
    """Транзакции реселлеров."""
    __tablename__ = "reseller_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reseller_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # topup, create_user, renew_user
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # target user
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResellerUser(Base):
    """Пользователи, созданные реселлерами."""
    __tablename__ = "reseller_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reseller_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    tariff_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AutoRenewal(Base):
    """Автоматическое продление подписок."""
    __tablename__ = "auto_renewals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    tariff_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # FK to TariffPlan
    payment_method: Mapped[str] = mapped_column(String(32), default="cryptopay")  # cryptopay/platega/card
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_renewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_renewal_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Server(Base):
    """Marzban серверы для multi-server управления."""
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    marzban_url: Mapped[str] = mapped_column(String(512), nullable=False)
    marzban_username: Mapped[str] = mapped_column(String(128), nullable=False)
    marzban_password: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet encrypted
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_master: Mapped[bool] = mapped_column(Boolean, default=False)
    country: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    max_users: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_users: Mapped[int] = mapped_column(Integer, default=0)
    total_bandwidth: Mapped[int] = mapped_column(BigInteger, default=0)  # bytes
    status: Mapped[str] = mapped_column(String(16), default="offline")  # online/offline
    last_check_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BrandingSettings(Base):
    """White-label branding settings."""
    __tablename__ = "branding_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_name: Mapped[str] = mapped_column(String(128), default="Nemo Tracker")
    logo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    favicon_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    primary_color: Mapped[str] = mapped_column(String(7), default="#6c5ce7")
    secondary_color: Mapped[str] = mapped_column(String(7), default="#2d3436")
    accent_color: Mapped[str] = mapped_column(String(7), default="#00cec9")
    dark_mode_default: Mapped[bool] = mapped_column(Boolean, default=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    company_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    support_email: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    telegram_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    custom_css: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_js: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    footer_text: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    og_image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ScalingPolicy(Base):
    """Политики авто-скейлинга серверов."""
    __tablename__ = "scaling_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    min_nodes: Mapped[int] = mapped_column(Integer, default=1)
    max_nodes: Mapped[int] = mapped_column(Integer, default=10)
    scale_up_threshold_cpu: Mapped[int] = mapped_column(Integer, default=80)
    scale_up_threshold_users: Mapped[int] = mapped_column(Integer, default=200)
    scale_up_threshold_bandwidth_percent: Mapped[int] = mapped_column(Integer, default=90)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=30)
    provider: Mapped[str] = mapped_column(String(32), default="hetzner")  # hetzner/digitalocean/vultr/custom
    provider_api_token: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    server_type: Mapped[str] = mapped_column(String(32), default="cx22")
    region: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    image_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    marzban_template_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    last_scaled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScalingEvent(Base):
    """События авто-скейлинга."""
    __tablename__ = "scaling_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)  # scale_up / scale_down
    server_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/provisioning/ready/failed
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Alert(Base):
    """Уведомления и предупреждения."""
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)  # new_user, traffic_80, expiring_3d, online, offline
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
