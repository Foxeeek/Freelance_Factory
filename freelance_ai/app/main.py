from __future__ import annotations

import asyncio
import logging

from freelance_ai.app.config import get_settings
from freelance_ai.app.database import init_db
from freelance_ai.bot.handlers import build_callback_handler
from freelance_ai.bot.telegram_bot import TelegramNotifier
from freelance_ai.services.scheduler import OrderScheduler


async def run() -> None:
    settings = get_settings()

    init_db()

    notifier = TelegramNotifier(settings)
    app = notifier.build_application()
    app.add_handler(build_callback_handler())

    scheduler = OrderScheduler(settings, notifier)
    scheduler.start()

    # Run first fetch immediately.
    await scheduler.fetch_and_notify()

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    logging.getLogger(__name__).info("Freelance AI aggregator started")
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def main() -> None:
    configure_logging()
    asyncio.run(run())


if __name__ == "__main__":
    main()
