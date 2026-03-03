from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from freelance_ai.app.config import Settings
from freelance_ai.app.database import get_session
from freelance_ai.bot.telegram_bot import TelegramNotifier
from freelance_ai.core.analyzer import analyze_order
from freelance_ai.core.platform_registry import build_registry
from freelance_ai.services.order_service import OrderService

logger = logging.getLogger(__name__)


class OrderScheduler:
    def __init__(self, settings: Settings, notifier: TelegramNotifier):
        self.settings = settings
        self.notifier = notifier
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        self.scheduler.add_job(
            self.fetch_and_notify,
            trigger="interval",
            minutes=self.settings.poll_interval_minutes,
            id="fetch-orders",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info("Scheduler started with %s min interval", self.settings.poll_interval_minutes)

    async def fetch_and_notify(self) -> None:
        registry = build_registry(self.settings)
        if not registry:
            logger.warning("No enabled platforms configured")
            return

        for platform_name, platform in registry.items():
            try:
                raw_orders = await platform.fetch_orders()
            except Exception as exc:
                logger.exception("Platform fetch failed (%s): %s", platform_name, exc)
                continue

            if not raw_orders:
                logger.info("No orders fetched from %s", platform_name)
                continue

            for raw_order in raw_orders:
                try:
                    normalized = platform.parse(raw_order)
                    analysis = analyze_order(
                        normalized,
                        hourly_rate_eur=self.settings.hourly_rate_eur,
                        default_language=self.settings.default_language,
                    )

                    if analysis is None:
                        logger.info("Skipping non-coding project: %s", normalized.external_id)
                        continue

                    with get_session() as session:
                        service = OrderService(session)
                        order, is_new = service.upsert_order(normalized)
                        service.save_analysis(order, analysis)

                        if is_new and order.status == "NEW":
                            sent = await self.notifier.send_order_for_review(order, analysis)
                            if sent:
                                service.mark_sent(order.id)
                except Exception as exc:
                    logger.exception("Failed to process order on %s: %s", platform_name, exc)
