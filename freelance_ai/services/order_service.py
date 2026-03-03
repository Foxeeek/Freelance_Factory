from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from freelance_ai.core.models import OrderAnalysis, OrderDB, OrderIn, OrderStatus


class OrderService:
    def __init__(self, session: Session):
        self.session = session

    def upsert_order(self, order_in: OrderIn) -> tuple[OrderDB, bool]:
        stmt = select(OrderDB).where(
            OrderDB.platform == order_in.platform,
            OrderDB.external_id == order_in.external_id,
        )
        existing = self.session.scalar(stmt)

        if existing:
            existing.title = order_in.title
            existing.url = order_in.url
            existing.description = order_in.description
            existing.budget = order_in.budget
            existing.currency = order_in.currency
            return existing, False

        order = OrderDB(
            platform=order_in.platform,
            external_id=order_in.external_id,
            title=order_in.title,
            url=order_in.url,
            description=order_in.description,
            budget=order_in.budget,
            currency=order_in.currency,
            status=OrderStatus.NEW.value,
        )
        self.session.add(order)
        self.session.flush()
        return order, True

    def save_analysis(self, order: OrderDB, analysis: OrderAnalysis) -> None:
        order.difficulty = analysis.difficulty
        order.codex_fit = analysis.codex_fit
        order.detected_stack = ",".join(analysis.detected_stack)
        order.estimated_hours_min = analysis.estimated_hours_range[0]
        order.estimated_hours_max = analysis.estimated_hours_range[1]
        order.estimated_price_min = analysis.estimated_price_range[0]
        order.estimated_price_max = analysis.estimated_price_range[1]
        order.risk_flags = ",".join(analysis.risk_flags)
        order.analysis_language = analysis.language

    def mark_sent(self, order_id: int) -> None:
        order = self.session.get(OrderDB, order_id)
        if order and order.status == OrderStatus.NEW.value:
            order.status = OrderStatus.SENT.value

    def mark_approved(self, order_id: int) -> OrderDB | None:
        order = self.session.get(OrderDB, order_id)
        if order:
            order.status = OrderStatus.APPROVED.value
        return order

    def mark_rejected(self, order_id: int, reason: str) -> OrderDB | None:
        order = self.session.get(OrderDB, order_id)
        if order:
            order.status = OrderStatus.REJECTED.value
            order.rejection_reason = reason
        return order
