from __future__ import annotations

from freelance_ai.core.models import OrderAnalysis, OrderDB


def generate_proposal(order: OrderDB, analysis: OrderAnalysis, language: str = "en") -> str:
    if language == "ua":
        return (
            f"Вітаю!\n\n"
            f"Я готовий виконати проєкт: {order.title}.\n"
            f"Орієнтовна складність: {analysis.difficulty}/10, очікувано {analysis.estimated_hours_range[0]}-"
            f"{analysis.estimated_hours_range[1]} годин.\n"
            f"Орієнтовний бюджет: €{analysis.estimated_price_range[0]}-€{analysis.estimated_price_range[1]}.\n\n"
            "Маю досвід з API інтеграціями, автоматизацією та розробкою Python-рішень. "
            "Готовий обговорити деталі та почати роботу найближчим часом."
        )

    return (
        f"Hello!\n\n"
        f"I can help with your project: {order.title}.\n"
        f"Estimated complexity: {analysis.difficulty}/10, expected {analysis.estimated_hours_range[0]}-"
        f"{analysis.estimated_hours_range[1]} hours.\n"
        f"Estimated budget: €{analysis.estimated_price_range[0]}-€{analysis.estimated_price_range[1]}.\n\n"
        "I have hands-on experience with API integrations, automation, and Python solutions. "
        "Happy to discuss requirements and start quickly."
    )
