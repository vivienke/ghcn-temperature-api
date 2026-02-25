from __future__ import annotations

from app.core.constants import PERIODS

def month_to_season_northern(month: int) -> str:
    if 3 <= month <= 5:
        return "SPRING"
    if 6 <= month <= 8:
        return "SUMMER"
    if 9 <= month <= 11:
        return "AUTUMN"
    return "WINTER"  # 12,1,2

def season_for_month(month: int, is_southern: bool) -> str:
    season_name = month_to_season_northern(month)
    if not is_southern:
        return season_name
    # invert seasons for southern hemisphere (meteorological)
    season_map = {
        "WINTER": "SUMMER",
        "SPRING": "AUTUMN",
        "SUMMER": "WINTER",
        "AUTUMN": "SPRING",
    }
    return season_map[season_name]

def period_year_for_season(year: int, month: int, season: str, is_southern: bool) -> int:
    """
    Winter (north) spans Dec-Feb -> Dec counts to next year.
    For south, SUMMER spans Dec-Feb -> Dec counts to next year (because SUMMER becomes boundary).
    """
    boundary_season = "SUMMER" if is_southern else "WINTER"
    if month == 12 and season == boundary_season:
        return year + 1
    return year
