from __future__ import annotations

from sqlalchemy.orm import Session

from freelance_ai.core.models import Settings


SETTINGS_SINGLETON_ID = 1


def get_settings(session: Session) -> Settings:
    settings = session.get(Settings, SETTINGS_SINGLETON_ID)
    if settings:
        return settings

    settings = Settings(id=SETTINGS_SINGLETON_ID, budget_filter_enabled=False, min_budget=0.0)
    session.add(settings)
    session.flush()
    return settings


def update_budget_filter(session: Session, enabled: bool) -> Settings:
    settings = get_settings(session)
    settings.budget_filter_enabled = enabled
    session.flush()
    return settings


def update_min_budget(session: Session, value: float) -> Settings:
    settings = get_settings(session)
    settings.min_budget = max(0.0, value)
    session.flush()
    return settings
