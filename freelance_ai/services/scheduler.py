from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from freelance_ai.app.config import Settings
from freelance_ai.app.database import get_session
from freelance_ai.bot.telegram_bot import TelegramNotifier
from freelance_ai.core.analyzer import analyze_order
from freelance_ai.core.models import OrderDB
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

            total_fetched = len(raw_orders)
            if not raw_orders:
                logger.info("No orders fetched from %s", platform_name)
                continue

            normalized_orders = []
            for raw_order in raw_orders:
                try:
                    normalized_orders.append(platform.parse(raw_order))
                except Exception as exc:
                    logger.exception("Failed to normalize order on %s: %s", platform_name, exc)

            if not normalized_orders:
                logger.info("No valid orders after normalization on %s", platform_name)
                continue

            parsed_ids = [order.external_id for order in normalized_orders]
            with get_session() as session:
                existing_ids = set(
                    session.scalars(
                        select(OrderDB.external_id).where(
                            OrderDB.platform == platform_name,
                            OrderDB.external_id.in_(parsed_ids),
                        )
                    )
                )

            existing_count = len(existing_ids)
            new_count = sum(1 for order in normalized_orders if order.external_id not in existing_ids)
            logger.info("Total parsed from page: %d", len(normalized_orders))
            logger.info("Already in DB: %d", existing_count)
            logger.info("New detected: %d", new_count)

            filtered_by_category = 0
            new_stored = 0
            sent_to_telegram = 0

            for normalized in normalized_orders:
                try:
                    with get_session() as session:
                        analysis = analyze_order(
                            normalized,
                            hourly_rate_eur=self.settings.hourly_rate_eur,
                            default_language=self.settings.default_language,
                            session=session,
                        )

                        if analysis is None:
                            filtered_by_category += 1
                            logger.info("Skipping order %s - no analysis", normalized.external_id)
                            continue

                        service = OrderService(session)
                        order, is_new = service.upsert_order(normalized)

                        if is_new:
                            new_stored += 1

                        service.save_analysis(order, analysis)

                        if is_new and order.status == "NEW":
                            sent = await self.notifier.send_order_for_review(order, analysis)
                            if sent:
                                service.mark_sent(order.id)
                                sent_to_telegram += 1
                except Exception as exc:
                    logger.exception("Failed to process order on %s: %s", platform_name, exc)

            logger.info(
                "Fetch cycle summary (%s): total_fetched=%d, total_parsed=%d, filtered_by_category=%d, "
                "new_stored=%d, sent_to_telegram=%d",
                platform_name,
                total_fetched,
                len(normalized_orders),
                filtered_by_category,
                new_stored,
                sent_to_telegram,
            )
