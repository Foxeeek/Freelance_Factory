from __future__ import annotations

from freelance_ai.app.config import Settings
from freelance_ai.platforms.base import BasePlatform
from freelance_ai.platforms.freelancehunt import FreelancehuntPlatform


def build_registry(settings: Settings) -> dict[str, BasePlatform]:
    all_platforms: dict[str, BasePlatform] = {
        "freelancehunt": FreelancehuntPlatform(),
    }

    enabled = {name.strip().lower() for name in settings.enabled_platforms}
    return {name: platform for name, platform in all_platforms.items() if name in enabled}
