from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from app.services.data_service import download_stream
from app.services.metadata_store import metadata_store

AWS_BASE = "https://noaa-ghcn-pds.s3.amazonaws.com"
BY_STATION_URL = f"{AWS_BASE}/csv.gz/by_station/{{station_id}}.csv.gz"


ELEMENTS: Tuple[str, str] = ("TMIN", "TMAX")
PERIODS: Tuple[str, str, str, str, str] = ("YEAR", "SPRING", "SUMMER", "AUTUMN", "WINTER")

# by_station hat keinen Header:
# 0 ID, 1 DATE(YYYYMMDD), 2 ELEMENT, 3 DATA_VALUE, 4 MFLAG, 5 QFLAG, 6 SFLAG, 7 OBS_TIME
COLS = ["ID", "DATE", "ELEMENT", "VALUE", "MFLAG", "QFLAG", "SFLAG", "OBS_TIME"]


def compute_temperature_series(
    cache_dir: str,
    station_id: str,
    start_year: int,
    end_year: int,
    ignore_qflag: bool = True,
) -> Tuple[List[int], Dict[str, List[Optional[float]]]]:
    """
    years[] + series-map (neutral, geeignet für Charts und Tabellen)
      years: [start_year..end_year]
      series keys: YEAR_TMIN, YEAR_TMAX, SPRING_TMIN, ..., WINTER_TMAX
      values: Arrays (len == len(years)), None = null bei fehlenden Daten
    """
    _ensure_station_known(cache_dir, station_id)

    years = _build_year_axis(start_year, end_year)
    series = _empty_series(years)

    is_southern = _is_southern_hemisphere(station_id)

    gz_path = ensure_station_file(cache_dir, station_id)
    df = _load_daily_df(gz_path, station_id, ignore_qflag)

    if df.empty:
        return years, series

    df = _add_time_cols(df)
    df = _add_period_views(df, is_southern)

    df = _filter_period_year_range(df, start_year, end_year)
    if df.empty:
        return years, series

    table = _aggregate_means(df)
    _fill_series(series, years, table)

    return years, series


# -----------------------------
# File handling / download
# -----------------------------

def _station_cache_path(cache_dir: str, station_id: str) -> Path:
    return Path(cache_dir) / "by_station" / f"{station_id}.csv.gz"


def ensure_station_file(cache_dir: str, station_id: str) -> Path:
    path = _station_cache_path(cache_dir, station_id)
    if not path.exists():
        download_stream(BY_STATION_URL.format(station_id=station_id), path)
    return path


# -----------------------------
# Metadata / hemisphere
# -----------------------------

def _ensure_station_known(cache_dir: str, station_id: str) -> None:
    metadata_store.ensure_loaded(cache_dir)
    if station_id not in metadata_store.stations_by_id:
        raise KeyError("station_not_found")


def _is_southern_hemisphere(station_id: str) -> bool:
    station = metadata_store.stations_by_id[station_id]
    lat = float(station.lat)  # falls anders: station.latitude
    return lat < 0


# -----------------------------
# Data loading
# -----------------------------

def _load_daily_df(gz_path: Path, station_id: str, ignore_qflag: bool) -> pd.DataFrame:
    df = pd.read_csv(
        gz_path,
        compression="gzip",
        header=None,
        names=COLS,
        usecols=["ID", "DATE", "ELEMENT", "VALUE", "QFLAG"],
        dtype={
            "ID": "string",
            "DATE": "string",
            "ELEMENT": "string",
            "VALUE": "int32",
            "QFLAG": "string",
        },
        low_memory=True,
    )

    df = _filter_daily_rows(df, station_id, ignore_qflag)
    df = _convert_units(df)

    return df[["DATE", "ELEMENT", "valueC"]]


def _filter_daily_rows(df: pd.DataFrame, station_id: str, ignore_qflag: bool) -> pd.DataFrame:
    df = df[df["ID"] == station_id]
    df = df[df["ELEMENT"].isin(ELEMENTS)]
    df = df[df["VALUE"] != -9999]
    if ignore_qflag:
        df = df[df["QFLAG"].fillna("") == ""]
    return df


def _convert_units(df: pd.DataFrame) -> pd.DataFrame:
    df["valueC"] = df["VALUE"] / 10.0
    return df


# -----------------------------
# Derivations (year/month, period/periodYear)
# -----------------------------

def _add_time_cols(df: pd.DataFrame) -> pd.DataFrame:
    df["year"] = df["DATE"].str.slice(0, 4).astype("int32")
    df["month"] = df["DATE"].str.slice(4, 6).astype("int8")
    return df


def _add_period_views(df: pd.DataFrame, is_southern: bool) -> pd.DataFrame:
    season_df = _build_season_view(df, is_southern)
    year_df = _build_year_view(df)
    return pd.concat([year_df, season_df], ignore_index=True)


def _build_year_view(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["period"] = "YEAR"
    out["periodYear"] = out["year"]
    return out[["periodYear", "period", "ELEMENT", "valueC"]]


def _build_season_view(df: pd.DataFrame, is_southern: bool) -> pd.DataFrame:
    out = df.copy()

    out["season"] = "WINTER"
    out.loc[out["month"].between(3, 5), "season"] = "SPRING"
    out.loc[out["month"].between(6, 8), "season"] = "SUMMER"
    out.loc[out["month"].between(9, 11), "season"] = "AUTUMN"

    if is_southern:
        out["season"] = out["season"].map(
            {
                "WINTER": "SUMMER",
                "SPRING": "AUTUMN",
                "SUMMER": "WINTER",
                "AUTUMN": "SPRING",
            }
        )

    boundary = "SUMMER" if is_southern else "WINTER"
    out["periodYear"] = out["year"]

    dec_mask = (out["month"] == 12) & (out["season"] == boundary)
    out.loc[dec_mask, "periodYear"] = out.loc[dec_mask, "year"] + 1

    out["period"] = out["season"]
    return out[["periodYear", "period", "ELEMENT", "valueC"]]


def _filter_period_year_range(df: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    return df[(df["periodYear"] >= start_year) & (df["periodYear"] <= end_year)]


# -----------------------------
# Aggregation & output
# -----------------------------

def _aggregate_means(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["periodYear", "period", "ELEMENT"])["valueC"]
        .mean()
        .unstack("ELEMENT")
        .reset_index()
    )


def _build_year_axis(start_year: int, end_year: int) -> List[int]:
    return list(range(start_year, end_year + 1))


def _empty_series(years: List[int]) -> Dict[str, List[Optional[float]]]:
    n = len(years)
    out: Dict[str, List[Optional[float]]] = {}
    for period in PERIODS:
        for element in ELEMENTS:
            out[f"{period}_{element}"] = [None] * n
    return out


def _fill_series(series: Dict[str, List[Optional[float]]], years: List[int], table: pd.DataFrame) -> None:
    start_year = years[0]
    n = len(years)

    for _, row in table.iterrows():
        y = int(row["periodYear"])
        period = str(row["period"])
        idx = y - start_year
        if idx < 0 or idx >= n:
            continue

        _set_value(series, period, "TMIN", idx, row.get("TMIN"))
        _set_value(series, period, "TMAX", idx, row.get("TMAX"))


def _set_value(
    series: Dict[str, List[Optional[float]]],
    period: str,
    element: str,
    idx: int,
    raw_value,
) -> None:
    key = f"{period}_{element}"
    series[key][idx] = _round_or_none(raw_value)


def _round_or_none(x) -> Optional[float]:
    if x is None or pd.isna(x):
        return None
    return round(float(x), 1)
