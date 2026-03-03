from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from freelance_ai.core.models import OrderAnalysis, OrderIn
from freelance_ai.core.scorer import estimate_hours_range, estimate_price_range
from freelance_ai.services.settings_service import get_settings

logger = logging.getLogger(__name__)


HIGH_COMPLEXITY_KEYWORDS = {
    "payments": 2,
    "mobile": 2,
    "blockchain": 3,
    "highload": 3,
    "kubernetes": 3,
    "kernel": 3,
    "driver": 3,
    "pentest": 2,
}

MID_COMPLEXITY_KEYWORDS = {
    "api": 1,
    "integration": 1,
    "scraping": 1,
    "automation": 1,
    "crm": 1,
}

LOW_FIT_KEYWORDS = {"blockchain", "kernel", "driver", "kubernetes", "pentest", "highload", "enterprise"}
HIGH_FIT_KEYWORDS = {"crud", "api", "integration", "automation", "bot", "scraping"}
STACK_KEYWORDS = {
    "python",
    "django",
    "flask",
    "fastapi",
    "react",
    "vue",
    "node",
    "postgres",
    "mysql",
    "docker",
    "kubernetes",
    "telegram",
    "wordpress",
}

BUILDABLE_KEYWORDS = [
    "python",
    "django",
    "fastapi",
    "flask",
    "api",
    "backend",
    "scraper",
    "bot",
    "automation",
    "parser",
    "frontend",
    "react",
    "vue",
    "javascript",
    "typescript",
    "web app",
    "website",
    "landing page",
    "html",
    "css",
    "wordpress",
    "shopify",
    "opencart",
    "bitrix",
    "cms",
    "plugin",
    "woocommerce",
    "ios",
    "android",
    "mobile app",
    "pwa",
    "php",
    "laravel",
    "ai",
    "machine learning",
    "ml",
    "chatbot",
    "openai",
    "sql",
    "database",
    "postgres",
    "mysql",
    "integration",
    "telegram bot",
    "payment system",
]

SEO_KEYWORDS = ["seo"]
MARKETING_KEYWORDS = ["marketing", "smm", "ads"]
TRANSLATION_KEYWORDS = ["translation", "translate", "перевод", "переклад"]

_skipped_projects_count = 0


def detect_category(title: str, description: str) -> str:
    text = f"{title} {description}".lower()

    if any(keyword in text for keyword in BUILDABLE_KEYWORDS):
        return "buildable"
    if any(keyword in text for keyword in TRANSLATION_KEYWORDS):
        return "translation"
    if any(keyword in text for keyword in SEO_KEYWORDS):
        return "seo"
    if any(keyword in text for keyword in MARKETING_KEYWORDS):
        return "marketing"
    return "other"


def _parse_budget_value(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.replace(" ", "").replace(",", ".")
    matches = re.findall(r"\d+(?:\.\d+)?", cleaned)
    if not matches:
        return None
    try:
        return float(matches[0])
    except ValueError:
        return None


def analyze_order(
    order: OrderIn,
    hourly_rate_eur: int,
    default_language: str = "en",
    session: Session | None = None,
) -> OrderAnalysis | None:
    global _skipped_projects_count

    category = detect_category(order.title, order.description)
    logger.info("Category detected: %s", category)

    if category == "other":
        _skipped_projects_count += 1
        logger.info("Skipped non-buildable projects: %d", _skipped_projects_count)
        return None

    if session is not None:
        app_settings = get_settings(session)
        budget_value = _parse_budget_value(order.budget)
        if app_settings.budget_filter_enabled and budget_value is not None and budget_value < app_settings.min_budget:
            logger.info("Filtered by budget")
            return None

    text = f"{order.title} {order.description}".lower()

    difficulty = 2
    for keyword, boost in MID_COMPLEXITY_KEYWORDS.items():
        if keyword in text:
            difficulty += boost
    for keyword, boost in HIGH_COMPLEXITY_KEYWORDS.items():
        if keyword in text:
            difficulty += boost
    difficulty = max(1, min(10, difficulty))

    codex_fit = 55
    codex_fit += sum(8 for kw in HIGH_FIT_KEYWORDS if kw in text)
    codex_fit -= sum(18 for kw in LOW_FIT_KEYWORDS if kw in text)
    codex_fit = max(0, min(100, codex_fit))

    detected_stack = sorted([kw for kw in STACK_KEYWORDS if kw in text])

    risk_flags: list[str] = []
    if "enterprise" in text:
        risk_flags.append("enterprise")
    if "login" in text or "auth" in text:
        risk_flags.append("login_required")
    if len(order.description.strip()) < 40:
        risk_flags.append("unknown_scope")

    hours_range = estimate_hours_range(difficulty)
    price_range = estimate_price_range(hours_range, hourly_rate_eur)

    return OrderAnalysis(
        difficulty=difficulty,
        codex_fit=codex_fit,
        detected_stack=detected_stack,
        estimated_hours_range=hours_range,
        estimated_price_range=price_range,
        risk_flags=risk_flags,
        language=default_language,
    )
