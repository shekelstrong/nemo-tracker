"""Nemo Tracker — Forecasting & Analytics (heuristic + linear regression)."""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, desc
from loguru import logger

from src.models import async_session
from src.models.database import User, Analytics, DailyRevenue, Transaction, Server


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _linear_regression(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Simple OLS: returns (slope, intercept)."""
    n = len(xs)
    if n < 2:
        return 0.0, ys[0] if ys else 0.0
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if denom == 0:
        return 0.0, sy / n
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return slope, intercept


# ---------------------------------------------------------------------------
# Churn prediction
# ---------------------------------------------------------------------------

async def predict_churn() -> list[dict]:
    """
    Predict churn risk for active users.
    
    Heuristics:
    - expire < 7 days + inactive > 3 days → high churn probability
    - Falling traffic (last 7d vs previous 7d) → medium risk
    - expire < 14 days → low baseline risk
    """
    now = datetime.utcnow()
    result = []

    async with async_session() as session:
        users = (await session.execute(
            select(User).where(User.status == "active")
        )).scalars().all()

        for u in users:
            prob = 0.0
            reasons = []

            # Check expire proximity
            days_to_expire = None
            if u.expire:
                delta = (u.expire.replace(tzinfo=None) - now).total_seconds() / 86400
                days_to_expire = round(delta, 1)

            # Check inactivity
            days_inactive = None
            if u.online_at:
                inactive = (now - u.online_at.replace(tzinfo=None)).total_seconds() / 86400
                days_inactive = round(inactive, 1)
            else:
                # Never been online
                days_inactive = 999

            # Rule 1: expiring soon + inactive
            if days_to_expire is not None and days_to_expire < 7 and days_inactive is not None and days_inactive > 3:
                prob = 0.8 + 0.1 * min(days_inactive / 30, 1.0)
                reasons.append("expiring_inactive")
            elif days_to_expire is not None and days_to_expire < 3:
                prob = max(prob, 0.7)
                reasons.append("expiring_very_soon")
            elif days_to_expire is not None and days_to_expire < 7:
                prob = max(prob, 0.4)
                reasons.append("expiring_soon")

            # Rule 2: long inactivity regardless of expire
            if days_inactive is not None and days_inactive > 14:
                prob = max(prob, 0.6)
                reasons.append("long_inactive")
            elif days_inactive is not None and days_inactive > 7:
                prob = max(prob, 0.3)
                reasons.append("inactive_week")

            # Rule 3: traffic drop — compare recent vs older analytics for this user
            # We approximate with overall traffic data since per-user daily is not stored
            # Use user's used_traffic as a proxy: if very low usage relative to limit
            if u.data_limit and u.data_limit > 0:
                usage_pct = (u.used_traffic or 0) / u.data_limit
                if usage_pct < 0.05 and days_to_expire is not None and days_to_expire < 14:
                    prob = max(prob, 0.3)
                    reasons.append("low_usage")

            prob = min(prob, 1.0)

            if prob > 0:
                risk = "high" if prob >= 0.6 else ("medium" if prob >= 0.3 else "low")
                result.append({
                    "username": u.username,
                    "expire": u.expire.strftime("%d.%m.%Y") if u.expire else None,
                    "days_to_expire": days_to_expire,
                    "days_inactive": days_inactive,
                    "churn_probability": round(prob, 2),
                    "risk_level": risk,
                    "reasons": reasons,
                })

    result.sort(key=lambda x: x["churn_probability"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# Resource exhaustion prediction
# ---------------------------------------------------------------------------

async def predict_resource_exhaustion() -> dict:
    """
    Predict when resources will be exhausted based on growth trends.
    
    Uses analytics data for user growth and server capacity.
    """
    now = datetime.utcnow()
    days_30 = (now - timedelta(days=30)).date()

    async with async_session() as session:
        # Get daily analytics for growth rate
        rows = (await session.execute(
            select(Analytics)
            .where(Analytics.date >= days_30)
            .order_by(Analytics.date)
        )).scalars().all()

        if len(rows) < 2:
            return {
                "days_until_cpu_full": None,
                "days_until_disk_full": None,
                "days_until_bw_full": None,
                "growth_rate": 0.0,
                "current_users": 0,
                "recommendation": None,
            }

        # User growth rate (users/day)
        user_counts = [r.total_users for r in rows if r.total_users > 0]
        if len(user_counts) >= 2:
            xs = list(range(len(user_counts)))
            slope, _ = _linear_regression([float(x) for x in xs], [float(y) for y in user_counts])
            growth_rate = slope  # users per day
        else:
            growth_rate = 0.0

        current_total = user_counts[-1] if user_counts else 0

        # Get server capacity
        servers = (await session.execute(
            select(Server).where(Server.is_active == True)
        )).scalars().all()

        total_max_users = sum(s.max_users or 0 for s in servers)
        total_bandwidth = sum(s.total_bandwidth or 0 for s in servers)

        # CPU estimate: rough heuristic — 100 users = ~10% CPU on typical VPS
        # Assume 100% CPU at ~1000 users per active server
        cpu_capacity = len(servers) * 1000 if servers else 1000
        days_until_cpu_full = None
        if growth_rate > 0 and cpu_capacity > 0:
            remaining = cpu_capacity - current_total
            if remaining > 0:
                days_until_cpu_full = round(remaining / growth_rate)
            else:
                days_until_cpu_full = 0

        # Disk: assume 1GB per user average, server has 50GB per node
        disk_capacity = len(servers) * 50  # GB
        days_until_disk_full = None
        if growth_rate > 0 and disk_capacity > 0:
            # Approximate current disk usage based on traffic
            avg_gb_per_user = 0.5  # conservative
            remaining_gb = disk_capacity - (current_total * avg_gb_per_user)
            if remaining_gb > 0:
                days_until_disk_full = round(remaining_gb / (growth_rate * avg_gb_per_user))
            else:
                days_until_disk_full = 0

        # Bandwidth: based on total bandwidth of servers
        days_until_bw_full = None
        if growth_rate > 0 and total_bandwidth > 0:
            # Avg daily traffic per user from analytics
            recent_traffic = [r.total_traffic_gb for r in rows[-7:] if r.total_traffic_gb]
            if recent_traffic and current_total > 0:
                avg_daily_per_user = (sum(recent_traffic) / len(recent_traffic)) / current_total
                total_bw_gb = total_bandwidth / (1024 ** 3)
                remaining_bw = total_bw_gb - (current_total * avg_daily_per_user * 30)  # monthly
                if remaining_bw > 0:
                    days_until_bw_full = round(remaining_bw / (growth_rate * avg_daily_per_user * 30) * 30)
                else:
                    days_until_bw_full = 0

        # Max users from servers
        if total_max_users > 0 and growth_rate > 0:
            days_until_users_full = round((total_max_users - current_total) / growth_rate)
        else:
            days_until_users_full = None

        # Recommendation
        recommendation = None
        if days_until_cpu_full is not None and days_until_cpu_full < 30:
            recommendation = {
                "en": f"Consider adding a new node within {days_until_cpu_full} days",
                "ru": f"Рекомендуется добавить ноду в течение {days_until_cpu_full} дней",
            }
        elif total_max_users > 0 and days_until_users_full is not None and days_until_users_full < 60:
            recommendation = {
                "en": f"User capacity will be reached in ~{days_until_users_full} days",
                "ru": f"Лимит пользователей будет достигнут через ~{days_until_users_full} дней",
            }

        return {
            "days_until_cpu_full": days_until_cpu_full,
            "days_until_disk_full": days_until_disk_full,
            "days_until_bw_full": days_until_bw_full,
            "days_until_users_full": days_until_users_full,
            "growth_rate": round(growth_rate, 2),
            "current_users": current_total,
            "total_capacity": total_max_users if total_max_users > 0 else None,
            "recommendation": recommendation,
        }


# ---------------------------------------------------------------------------
# Revenue prediction
# ---------------------------------------------------------------------------

async def predict_revenue() -> dict:
    """
    Forecast revenue using linear regression on daily revenue data.
    """
    now = datetime.utcnow()
    days_30 = (now - timedelta(days=30)).date()

    async with async_session() as session:
        # Try DailyRevenue first
        rev_rows = (await session.execute(
            select(DailyRevenue)
            .where(DailyRevenue.date >= days_30)
            .order_by(DailyRevenue.date)
        )).scalars().all()

        # If no DailyRevenue, fall back to aggregating Transaction table
        if not rev_rows:
            daily_data = []
            for i in range(29, -1, -1):
                d = (now - timedelta(days=i)).date()
                day_start = datetime(d.year, d.month, d.day)
                day_end = day_start + timedelta(days=1)
                total = await session.scalar(
                    select(func.coalesce(func.sum(Transaction.amount), 0))
                    .where(Transaction.status == "paid", Transaction.created_at >= day_start, Transaction.created_at < day_end)
                )
                daily_data.append({"date": d, "total_rub": float(total or 0)})
        else:
            daily_data = [{"date": r.date, "total_rub": r.total_rub or 0} for r in rev_rows]

    if len(daily_data) < 2:
        return {
            "daily_forecast": [],
            "total_7d": 0,
            "total_14d": 0,
            "total_30d": 0,
            "trend": "stable",
            "trend_direction": "→",
            "actual": [],
        }

    # Build regression on actual data
    actual = []
    for d in daily_data:
        actual.append({
            "date": d["date"].strftime("%d.%m") if hasattr(d["date"], "strftime") else str(d["date"]),
            "value": round(d["total_rub"], 2),
        })

    values = [d["total_rub"] for d in daily_data]
    xs = [float(i) for i in range(len(values))]
    slope, intercept = _linear_regression(xs, values)

    # Generate forecast for next 30 days
    daily_forecast = []
    total_7d = 0.0
    total_14d = 0.0
    total_30d = 0.0
    for i in range(1, 31):
        day_idx = len(values) + i - 1
        predicted = max(slope * day_idx + intercept, 0)
        forecast_date = (now + timedelta(days=i)).strftime("%d.%m")
        daily_forecast.append({
            "date": forecast_date,
            "value": round(predicted, 2),
        })
        if i <= 7:
            total_7d += predicted
        if i <= 14:
            total_14d += predicted
        total_30d += predicted

    # Determine trend
    if slope > 5:
        trend = "growing"
        trend_direction = "↑"
    elif slope < -5:
        trend = "declining"
        trend_direction = "↓"
    else:
        trend = "stable"
        trend_direction = "→"

    return {
        "daily_forecast": daily_forecast,
        "total_7d": round(total_7d, 2),
        "total_14d": round(total_14d, 2),
        "total_30d": round(total_30d, 2),
        "trend": trend,
        "trend_direction": trend_direction,
        "slope_per_day": round(slope, 2),
        "actual": actual,
    }
