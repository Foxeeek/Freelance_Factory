from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from freelance_ai.app.config import get_settings
from freelance_ai.app.database import get_session
from freelance_ai.core.models import OrderAnalysis, OrderDB
from freelance_ai.core.proposal_generator import generate_proposal
from freelance_ai.services.order_service import OrderService

logger = logging.getLogger(__name__)


def build_callback_handler() -> CallbackQueryHandler:
    return CallbackQueryHandler(handle_decision, pattern=r"^(approve|reject):\d+$")


async def handle_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    action, order_id_raw = query.data.split(":", maxsplit=1)
    order_id = int(order_id_raw)

    with get_session() as session:
        service = OrderService(session)

        if action == "approve":
            order = service.mark_approved(order_id)
            if not order:
                await query.edit_message_text("Order not found.")
                return

            analysis = _analysis_from_order(order)
            settings = get_settings()
            proposal = generate_proposal(order, analysis, settings.default_language)
            await query.edit_message_text(f"Approved order #{order.id}. Draft proposal generated.")
            await context.bot.send_message(chat_id=query.message.chat_id, text=proposal)
            logger.info("Order %s approved", order.id)
            return

        order = service.mark_rejected(order_id, _build_rejection_reason(session.get(OrderDB, order_id)))
        if not order:
            await query.edit_message_text("Order not found.")
            return

        await query.edit_message_text(f"Rejected order #{order.id}.")
        logger.info("Order %s rejected", order.id)


def _analysis_from_order(order: OrderDB) -> OrderAnalysis:
    return OrderAnalysis(
        difficulty=order.difficulty or 1,
        codex_fit=order.codex_fit or 0,
        detected_stack=(order.detected_stack.split(",") if order.detected_stack else []),
        estimated_hours_range=(order.estimated_hours_min or 1, order.estimated_hours_max or 3),
        estimated_price_range=(order.estimated_price_min or 0, order.estimated_price_max or 0),
        risk_flags=(order.risk_flags.split(",") if order.risk_flags else []),
        language=order.analysis_language or "en",
    )


def _build_rejection_reason(order: OrderDB | None) -> str:
    if not order or not order.risk_flags:
        return "manual_reject"
    return order.risk_flags
