from __future__ import annotations

import logging

import httpx

from freelance_ai.core.models import OrderIn
from freelance_ai.platforms.base import BasePlatform
from freelance_ai.platforms.freelancehunt.parser import parse_job_cards

logger = logging.getLogger(__name__)


class FreelancehuntPlatform(BasePlatform):
    platform_name = "freelancehunt"
    public_jobs_url = "https://freelancehunt.com/projects"

    async def fetch_orders(self) -> list[dict]:
        """Fetch raw projects from public pages.

        Placeholder strategy:
        - gracefully return [] on any failure
        - no auth/login needed
        TODO: implement robust pagination and anti-bot handling.
        """

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(self.public_jobs_url)
                response.raise_for_status()
                return parse_job_cards(response.text)
        except Exception as exc:
            logger.warning("Freelancehunt fetch failed: %s", exc)
            return []

    def parse(self, raw: dict) -> OrderIn:
        return OrderIn(
            platform=self.platform_name,
            external_id=str(raw.get("external_id", "")),
            title=str(raw.get("title", "Untitled")),
            url=str(raw.get("url", "")),
            description=str(raw.get("description", "")),
            budget=raw.get("budget"),
            currency=raw.get("currency"),
            language="ua",
        )
