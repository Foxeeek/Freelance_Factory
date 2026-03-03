from __future__ import annotations

from abc import ABC, abstractmethod

from freelance_ai.core.models import OrderIn


class BasePlatform(ABC):
    platform_name: str

    @abstractmethod
    async def fetch_orders(self) -> list[dict]:
        """Fetch raw orders from a source platform."""

    @abstractmethod
    def parse(self, raw: dict) -> OrderIn:
        """Parse one raw payload to normalized OrderIn."""
