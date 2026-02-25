from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd


def calculate_period_averages(period_df: pd.DataFrame) -> pd.DataFrame:
    return (
        period_df.groupby(["periodYear", "period", "ELEMENT"])["temperature_celsius"]
        .mean()
        .unstack("ELEMENT")
        .reset_index()
    )


def build_empty_series(
    years: List[int],
    periods: tuple[str, ...],
    elements: tuple[str, ...],
) -> Dict[str, List[Optional[float]]]:
    year_count = len(years)
    series: Dict[str, List[Optional[float]]] = {}
    for period in periods:
        for element in elements:
            series[f"{period}_{element}"] = [None] * year_count
    return series


def apply_series_values(
    series: Dict[str, List[Optional[float]]],
    years: List[int],
    period_avg_df: pd.DataFrame,
) -> None:
    first_year = years[0]
    year_count = len(years)

    for _, avg_row in period_avg_df.iterrows():
        period_year = int(avg_row["periodYear"])
        period = str(avg_row["period"])
        year_index = period_year - first_year
        if year_index < 0 or year_index >= year_count:
            continue

        _set_value(series, period, "TMIN", year_index, avg_row.get("TMIN"))
        _set_value(series, period, "TMAX", year_index, avg_row.get("TMAX"))


def _set_value(
    series: Dict[str, List[Optional[float]]],
    period: str,
    element: str,
    year_index: int,
    raw_celsius_value,
) -> None:
    series_key = f"{period}_{element}"
    series[series_key][year_index] = _round_or_none(raw_celsius_value)


def _round_or_none(value) -> Optional[float]:
    if value is None or pd.isna(value):
        return None
    return round(float(value), 1)
