"""Nemo Tracker — Main entry point (Этап 2)."""

import asyncio
import sys
from datetime import date
from loguru import logger

from src.models import init_db
from src.core.sync import sync_all_users, detect_changes, sync_system_stats
from src.core.analytics import calculate_daily_stats
from src.core.alerting import (
    check_new_users, check_online_status, check_traffic_limits, check_expiring_users
)
from src.core.log_reader import log_reader
from src.core.device_tracker import device_tracker


# Интервалы в секундах
SYNC_INTERVAL = 60       # Синхронизация + detect_changes
ANALYTICS_INTERVAL = 3600  # Каждый час
ALERTS_INTERVAL = 300      # Проверка лимитов/истечения каждые 5 мин


async def _run_periodically(coro_func, interval: int, name: str):
    """Запускает coro_func() каждые interval секунд."""
    while True:
        try:
            await coro_func()
        except Exception as e:
            logger.error(f"[{name}] Error: {e}")
        await asyncio.sleep(interval)


async def main():
    logger.info("🦈 Nemo Tracker starting (Stage 2)...")

    # 1. Инициализация БД
    await init_db()
    logger.info("📦 Database initialized")

    # 2. Первичная синхронизация
    total, new_count, new_usernames = await sync_all_users()
    logger.info(f"🔄 Initial sync: {total} users, {new_count} new")

    # 3. Системная статистика
    await sync_system_stats()

    # 4. Алерты на новых юзеров
    if new_usernames:
        await check_new_users(new_usernames)

    # 5. Первичная аналитика
    await calculate_daily_stats()

    logger.info("✅ Nemo Tracker is running")

    # 6. Синхронизируем лимиты устройств из БД
    await device_tracker.sync_device_limits_from_marzban()
    logger.info("📱 Device limits synced")

    # 7. Запускаем периодические задачи
    tasks = [
        asyncio.create_task(_run_periodically(_sync_and_detect, SYNC_INTERVAL, "sync")),
        asyncio.create_task(_run_periodically(_run_analytics, ANALYTICS_INTERVAL, "analytics")),
        asyncio.create_task(_run_periodically(_run_alerts, ALERTS_INTERVAL, "alerts")),
        asyncio.create_task(_run_periodically(device_tracker.sync_device_limits_from_marzban, 300, "device_sync")),
        asyncio.create_task(_run_log_reader()),
    ]

    # 8. Запускаем Web-админку в отдельном таске
    tasks.append(asyncio.create_task(_run_web()))

    # Ожидаем завершения (никогда не произойдёт в нормальном режиме)
    await asyncio.gather(*tasks)


async def _sync_and_detect():
    """Каждые 60 сек: синхронизация + detect changes + алерты на подключения."""
    _, new_count, new_usernames = await sync_all_users()
    went_online, went_offline = await detect_changes()

    if new_usernames:
        await check_new_users(new_usernames)
    if went_online or went_offline:
        await check_online_status(went_online, went_offline)


async def _run_analytics():
    """Каждый час: агрегация статистики."""
    await calculate_daily_stats()


async def _run_alerts():
    """Каждые 5 мин: проверка лимитов и истечения подписок."""
    await check_traffic_limits()
    await check_expiring_users(days_before=3)


async def _on_xray_connection(event: dict):
    """Callback: Xray лог зафиксировал подключение."""
    username = event.get("username", "")
    ip = event.get("ip", "")
    inbound = event.get("inbound", "")
    if not username or not ip:
        return
    
    # Записываем IP
    await device_tracker.record_ip(username, ip, inbound=inbound, source="xray")
    
    # Проверяем лимит устройств
    result = await device_tracker.check_and_enforce(username, inbound=inbound)
    if result:
        logger.info(f"Device enforcement: {result['message']}")


def _setup_log_reader():
    """Configure log reader with device tracking callback."""
    log_reader.on_connection(_on_xray_connection)


async def _run_log_reader():
    """Запуск чтения Xray логов через WebSocket."""
    _setup_log_reader()
    await log_reader.start()


async def _run_web():
    """Запуск FastAPI web-сервера."""
    import uvicorn
    from src.api.web import web_app as app
    from src.config import settings
    config = uvicorn.Config(app, host=settings.web_host, port=settings.web_port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Nemo Tracker stopped")
        sys.exit(0)
