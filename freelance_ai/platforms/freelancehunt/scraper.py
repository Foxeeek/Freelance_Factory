from __future__ import annotations

import asyncio
import logging
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from freelance_ai.core.models import OrderIn
from freelance_ai.platforms.base import BasePlatform

logger = logging.getLogger(__name__)

PROJECTS_URL = "https://freelancehunt.com/projects"
MAX_PAGES = 2


async def fetch_projects() -> list[dict]:
    """Fetch project cards from Freelancehunt projects list page.

    This function intentionally parses only the listing page and does not
    request project detail pages.
    """

    projects: list[dict] = []
    seen_ids: set[str] = set()
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            for page in range(1, MAX_PAGES + 1):
                try:
                    response = await client.get(PROJECTS_URL, params={"page": page})
                    response.raise_for_status()
                except Exception as exc:
                    logger.warning("Freelancehunt fetch failed for page %s: %s", page, exc)
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                table = soup.select_one("table.project-list")
                if not table:
                    logger.info("Freelancehunt: parsed 0 projects on page %s (table.project-list not found)", page)
                    continue

                page_projects = 0
                for link in table.select('a[href*="/project/"]'):
                    href = (link.get("href") or "").strip()
                    if not href:
                        continue

                    absolute_url = urljoin(PROJECTS_URL, href)
                    path = urlparse(absolute_url).path.rstrip("/")
                    last_segment = path.split("/")[-1] if path else ""
                    external_id = last_segment.replace(".html", "")
                    if not external_id or external_id in seen_ids:
                        continue

                    title = (link.get("title") or link.get_text(" ", strip=True) or "Untitled").strip()
                    seen_ids.add(external_id)
                    page_projects += 1

                    projects.append(
                        {
                            "external_id": external_id,
                            "title": title,
                            "url": absolute_url,
                            "description": title,
                            "budget": None,
                            "platform": "freelancehunt",
                        }
                    )

                logger.info("Freelancehunt: parsed %d projects from page %s", page_projects, page)
    except Exception as exc:
        logger.warning("Freelancehunt fetch failed: %s", exc)
        return []

    logger.info("Freelancehunt: parsed %d projects", len(projects))
    return projects


class FreelancehuntPlatform(BasePlatform):
    platform_name = "freelancehunt"

    async def fetch_orders(self) -> list[dict]:
        return await fetch_projects()

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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    asyncio.run(fetch_projects())
