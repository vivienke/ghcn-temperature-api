from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.logic.metadata_store import MetadataStore
from app.data.noaa_station_files import NoaaStationFiles

ELEMENTS: Tuple[str, str] = ("TMIN", "TMAX")
PERIODS: Tuple[str, str, str, str, str] = ("YEAR", "SPRING", "SUMMER", "AUTUMN", "WINTER")

# by_station has no header:
# 0 ID, 1 DATE(YYYYMMDD), 2 ELEMENT, 3 DATA_VALUE, 4 MFLAG, 5 QFLAG, 6 SFLAG, 7 OBS_TIME
COLS = ["ID", "DATE", "ELEMENT", "VALUE", "MFLAG", "QFLAG", "SFLAG", "OBS_TIME"]


class TemperatureSeriesService:
    def __init__(self, metadata: MetadataStore, station_files: NoaaStationFiles):
        self.metadata = metadata
        self.station_files = station_files

    def compute_temperature_series(
        self,
        station_id: str,
        start_year: int,
        end_year: int,
        ignore_qflag: bool = True,
    ) -> Tuple[List[int], Dict[str, List[Optional[float]]]]:
        self.metadata.ensure_loaded()
        if station_id not in self.metadata.stations_by_id:
            raise KeyError("station_not_found")

        years = list(range(start_year, end_year + 1))
        series = _empty_series(years)

        st = self.metadata.stations_by_id[station_id]
        is_southern = float(st.lat) < 0

        gz_path = self.station_files.ensure_station_gz(station_id)

        # chunked read + frühes Filtering (DATE, ID, ELEMENT, missing, QFLAG)
        df = _load_daily_df(
            gz_path=gz_path,
            station_id=station_id,
            ignore_qflag=ignore_qflag,
            start_year=start_year,
            end_year=end_year,
        )
        if df.empty:
            return years, series

        df = _add_time_cols(df)

        # YEAR + SEASONS (vektorisiert)
        df = _add_period_views(df, is_southern)

        # Period-year range (safety)
        df = df[(df["periodYear"] >= start_year) & (df["periodYear"] <= end_year)]
        if df.empty:
            return years, series

        table = (
            df.groupby(["periodYear", "period", "ELEMENT"])["valueC"]
            .mean()
            .unstack("ELEMENT")
            .reset_index()
        )

        _fill_series(series, years, table)
        return years, series


def _load_daily_df(
    gz_path: Path,
    station_id: str,
    ignore_qflag: bool,
    start_year: int,
    end_year: int,
) -> pd.DataFrame:
    """
    Lädt by_station .csv.gz chunked und filtert so früh wie möglich:
    - Datum (start_year..end_year)
    - ID == station_id (robust, auch wenn Datei mal nicht strikt 1 Station wäre)
    - ELEMENT in {TMIN, TMAX}
    - VALUE != -9999
    - optional QFLAG leer
    """
    start_date = f"{start_year}0101"
    end_date = f"{end_year}1231"

    chunks: List[pd.DataFrame] = []

    for chunk in pd.read_csv(
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
        chunksize=1_000_000, 
    ):
        # Früh filtern
        chunk = chunk[(chunk["DATE"] >= start_date) & (chunk["DATE"] <= end_date)]
        if chunk.empty:
            continue

        chunk = chunk[chunk["ID"] == station_id]
        if chunk.empty:
            continue

        chunk = chunk[chunk["ELEMENT"].isin(ELEMENTS)]
        if chunk.empty:
            continue

        chunk = chunk[chunk["VALUE"] != -9999]
        if chunk.empty:
            continue

        if ignore_qflag:
            chunk = chunk[chunk["QFLAG"].fillna("") == ""]
            if chunk.empty:
                continue

        chunks.append(chunk)

    if not chunks:
        return pd.DataFrame(columns=["DATE", "ELEMENT", "valueC"])

    df = pd.concat(chunks, ignore_index=True)
    df["valueC"] = df["VALUE"] / 10.0
    return df[["DATE", "ELEMENT", "valueC"]]


def _add_time_cols(df: pd.DataFrame) -> pd.DataFrame:
    df["year"] = df["DATE"].str.slice(0, 4).astype("int32")
    df["month"] = df["DATE"].str.slice(4, 6).astype("int8")
    return df


def _add_period_views(df: pd.DataFrame, is_southern: bool) -> pd.DataFrame:
    """
    Baut 2 Views:
    - YEAR: period="YEAR", periodYear=year
    - SEASON: meteorologische Jahreszeiten, periodYear mit Dec->Folgejahr bei Winter/Sommer (je Hemisphäre)
    """
    # YEAR view
    year_view = df.copy()
    year_view["period"] = "YEAR"
    year_view["periodYear"] = year_view["year"]

    # SEASON view (vektorisiert)
    season_view = df.copy()
    m = season_view["month"]

    # Northern meteorological seasons
    season = np.full(len(season_view), "WINTER", dtype=object)
    season[(m >= 3) & (m <= 5)] = "SPRING"
    season[(m >= 6) & (m <= 8)] = "SUMMER"
    season[(m >= 9) & (m <= 11)] = "AUTUMN"

    if is_southern:
        mapping = {"WINTER": "SUMMER", "SPRING": "AUTUMN", "SUMMER": "WINTER", "AUTUMN": "SPRING"}
        season = np.vectorize(mapping.get)(season)
        boundary = "SUMMER"  # südliche Hemisphäre: Sommer ist Dec-Feb
    else:
        boundary = "WINTER"  # nördliche Hemisphäre: Winter ist Dec-Feb

    season_view["period"] = season

    period_year = season_view["year"].copy()
    dec_boundary = (season_view["month"] == 12) & (season_view["period"] == boundary)
    period_year.loc[dec_boundary] = period_year.loc[dec_boundary] + 1
    season_view["periodYear"] = period_year

    out = pd.concat(
        [
            year_view[["periodYear", "period", "ELEMENT", "valueC"]],
            season_view[["periodYear", "period", "ELEMENT", "valueC"]],
        ],
        ignore_index=True,
    )
    return out


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


def _set_value(series: Dict[str, List[Optional[float]]], period: str, element: str, idx: int, raw_value) -> None:
    key = f"{period}_{element}"
    series[key][idx] = _round_or_none(raw_value)


def _round_or_none(x) -> Optional[float]:
    if x is None or pd.isna(x):
        return None
    return round(float(x), 1)
