from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from freelance_ai.app.config import get_settings
from freelance_ai.app.database import get_session
from freelance_ai.core.models import OrderAnalysis, OrderDB
from freelance_ai.core.proposal_generator import generate_proposal
from freelance_ai.services.order_service import OrderService
from freelance_ai.services.settings_service import (
    get_settings as get_runtime_settings,
)
from freelance_ai.services.settings_service import update_budget_filter, update_min_budget

logger = logging.getLogger(__name__)
AWAITING_MIN_BUDGET_KEY = "awaiting_min_budget"


def build_bot_handlers() -> list:
    return [
        CommandHandler("settings", settings_command),
        CallbackQueryHandler(handle_decision, pattern=r"^(approve|reject):\d+$"),
        CallbackQueryHandler(handle_settings_callback, pattern=r"^(toggle_budget_filter|set_min_budget)$"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_min_budget_input),
    ]


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return

    with get_session() as session:
        runtime_settings = get_runtime_settings(session)

    text = (
        f"Budget filter: {'ON' if runtime_settings.budget_filter_enabled else 'OFF'}\n"
        f"Min budget: {runtime_settings.min_budget:.2f} EUR"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Toggle Budget Filter", callback_data="toggle_budget_filter")],
            [InlineKeyboardButton("Set Min Budget", callback_data="set_min_budget")],
        ]
    )
    await update.effective_message.reply_text(text=text, reply_markup=keyboard)


async def handle_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    if query.data == "toggle_budget_filter":
        with get_session() as session:
            runtime_settings = get_runtime_settings(session)
            runtime_settings = update_budget_filter(session, not runtime_settings.budget_filter_enabled)

        await query.edit_message_text(
            text=(
                f"Budget filter: {'ON' if runtime_settings.budget_filter_enabled else 'OFF'}\n"
                f"Min budget: {runtime_settings.min_budget:.2f} EUR"
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Toggle Budget Filter", callback_data="toggle_budget_filter")],
                    [InlineKeyboardButton("Set Min Budget", callback_data="set_min_budget")],
                ]
            ),
        )
        return

    context.user_data[AWAITING_MIN_BUDGET_KEY] = True
    await query.message.reply_text("Please enter minimum budget as a number (EUR), e.g. 150")


async def handle_min_budget_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return

    if not context.user_data.get(AWAITING_MIN_BUDGET_KEY):
        return

    raw_text = (update.effective_message.text or "").strip().replace(",", ".")
    try:
        value = float(raw_text)
    except ValueError:
        await update.effective_message.reply_text("Invalid value. Please send a valid number, e.g. 150")
        return

    with get_session() as session:
        runtime_settings = update_min_budget(session, value)

    context.user_data[AWAITING_MIN_BUDGET_KEY] = False
    await update.effective_message.reply_text(
        f"Min budget updated to {runtime_settings.min_budget:.2f} EUR. "
        f"Budget filter is {'ON' if runtime_settings.budget_filter_enabled else 'OFF'}."
    )


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
            app_settings = get_settings()
            proposal = generate_proposal(order, analysis, app_settings.default_language)
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
