"""Nemo Tracker — Main entry point."""

import asyncio
import sys
from loguru import logger


async def main():
    logger.info("🦈 Nemo Tracker starting...")
    # TODO: Initialize components
    # 1. Connect to Marzban API
    # 2. Start log parser
    # 3. Start Telegram bot
    # 4. Start Web dashboard
    logger.info("✅ Nemo Tracker is running")
    await asyncio.Event().wait()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Nemo Tracker stopped")
        sys.exit(0)
