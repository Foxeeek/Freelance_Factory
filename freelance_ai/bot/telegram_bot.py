from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application

from freelance_ai.app.config import Settings
from freelance_ai.core.models import OrderAnalysis, OrderDB

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.app: Application | None = None

    def build_application(self) -> Application:
        if not self.settings.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required for Telegram bot.")
        self.app = Application.builder().token(self.settings.telegram_bot_token).build()
        return self.app

    async def send_order_for_review(self, order: OrderDB, analysis: OrderAnalysis) -> bool:
        if not self.app:
            logger.warning("Telegram app is not initialized.")
            return False

        if not self.settings.telegram_chat_id:
            logger.warning("TELEGRAM_CHAT_ID is empty; skipping message send.")
            return False

        message = (
            f"🆕 Order #{order.id}\n"
            f"Platform: {order.platform}\n"
            f"Title: {order.title}\n"
            f"URL: {order.url}\n"
            f"Difficulty: {analysis.difficulty}/10\n"
            f"Codex fit: {analysis.codex_fit}/100\n"
            f"Hours: {analysis.estimated_hours_range[0]}-{analysis.estimated_hours_range[1]}\n"
            f"Price EUR: {analysis.estimated_price_range[0]}-{analysis.estimated_price_range[1]}\n"
            f"Risks: {', '.join(analysis.risk_flags) if analysis.risk_flags else 'none'}"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve:{order.id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject:{order.id}"),
                ]
            ]
        )

        await self.app.bot.send_message(chat_id=self.settings.telegram_chat_id, text=message, reply_markup=keyboard)
        return True
