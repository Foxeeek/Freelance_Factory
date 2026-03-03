from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

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
        self.scheduler: AsyncIOScheduler | None = None
        self._last_tick_at: datetime | None = None
        self._watchdog_task: asyncio.Task | None = None

    def start(self) -> None:
        event_loop = asyncio.get_running_loop()
        self.scheduler = AsyncIOScheduler(event_loop=event_loop)
        self.scheduler.add_job(
            self.fetch_and_notify,
            trigger="interval",
            minutes=self.settings.poll_interval_minutes,
            id="fetch-orders",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=max(60, self.settings.poll_interval_minutes * 60),
        )
        self.scheduler.start()

        next_run_time = None
        jobs = self.scheduler.get_jobs()
        if jobs:
            next_run_time = jobs[0].next_run_time

        logger.info(
            "Scheduler started with %s min interval | next_run_time=%s",
            self.settings.poll_interval_minutes,
            next_run_time,
        )

        if not self._watchdog_task or self._watchdog_task.done():
            self._watchdog_task = event_loop.create_task(self._watchdog())

    async def stop(self) -> None:
        if self._watchdog_task and not self._watchdog_task.done():
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                pass

        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def _watchdog(self) -> None:
        check_interval_seconds = max(30, self.settings.poll_interval_minutes * 60)
        stale_after = timedelta(minutes=self.settings.poll_interval_minutes * 2)

        while True:
            await asyncio.sleep(check_interval_seconds)
            if self._last_tick_at is None:
                logger.warning("Scheduler watchdog: no scheduler tick has executed yet")
                continue

            elapsed = datetime.now(UTC) - self._last_tick_at
            if elapsed > stale_after:
                logger.warning(
                    "Scheduler watchdog: no tick for %ss (threshold=%ss)",
                    int(elapsed.total_seconds()),
                    int(stale_after.total_seconds()),
                )

    async def fetch_and_notify(self) -> None:
        try:
            now = datetime.now(UTC)
            self._last_tick_at = now
            logger.info("Scheduler tick started at %s", now.isoformat())

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
        except Exception:
            logger.exception("Scheduler job crashed")
        finally:
            logger.info("Scheduler tick finished")
