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


class Alert(Base):
    """Уведомления и предупреждения."""
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)  # new_user, traffic_80, expiring_3d, online, offline
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
