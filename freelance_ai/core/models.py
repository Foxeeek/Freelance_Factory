from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from freelance_ai.app.database import Base


class OrderStatus(str, Enum):
    NEW = "NEW"
    SENT = "SENT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(slots=True)
class OrderIn:
    platform: str
    external_id: str
    title: str
    url: str
    description: str
    budget: str | None = None
    currency: str | None = None
    language: str = "en"


@dataclass(slots=True)
class OrderAnalysis:
    difficulty: int
    codex_fit: int
    detected_stack: list[str]
    estimated_hours_range: tuple[int, int]
    estimated_price_range: tuple[int, int]
    risk_flags: list[str]
    language: str = "en"


class OrderDB(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("platform", "external_id", name="uq_orders_platform_external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    budget: Mapped[str | None] = mapped_column(String(64), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)

    status: Mapped[str] = mapped_column(String(32), default=OrderStatus.NEW.value, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    codex_fit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detected_stack: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_hours_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_hours_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_price_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_price_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_flags: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_language: Mapped[str | None] = mapped_column(String(8), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
