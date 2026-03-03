from __future__ import annotations

from bs4 import BeautifulSoup


def parse_job_cards(html: str) -> list[dict]:
    """Minimal BeautifulSoup parsing example for Freelancehunt job cards.

    NOTE: This is a placeholder parser for public pages and may need adaptation
    if Freelancehunt changes markup.
    """

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("article.project, div.project, div.job")
    parsed: list[dict] = []

    for card in cards:
        title_node = card.select_one("a[href]")
        title = title_node.get_text(strip=True) if title_node else "Untitled project"
        url = title_node.get("href", "") if title_node else ""

        description_node = card.select_one(".description, .project-description, p")
        description = description_node.get_text(" ", strip=True) if description_node else ""

        budget_node = card.select_one(".price, .budget, .project-price")
        budget = budget_node.get_text(" ", strip=True) if budget_node else None

        external_id = card.get("data-project-id") or card.get("id") or url or title

        parsed.append(
            {
                "external_id": str(external_id),
                "title": title,
                "url": url,
                "description": description,
                "budget": budget,
                "currency": "UAH",
            }
        )

    return parsed
