from __future__ import annotations


def estimate_hours_range(difficulty: int) -> tuple[int, int]:
    if difficulty <= 2:
        return (1, 3)
    if difficulty <= 4:
        return (4, 10)
    if difficulty <= 6:
        return (12, 24)
    if difficulty <= 8:
        return (30, 60)
    return (80, 160)


def estimate_price_range(hours_range: tuple[int, int], hourly_rate_eur: int) -> tuple[int, int]:
    return (hours_range[0] * hourly_rate_eur, hours_range[1] * hourly_rate_eur)
