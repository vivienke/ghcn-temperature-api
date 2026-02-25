from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple
import threading

from app.data.noaa_metadata_files import NoaaMetadataFiles
from app.models.station import Station, Availability
from app.exceptions import DataUnavailableError


class MetadataStore:
    def __init__(self, files: NoaaMetadataFiles):
        self.files = files
        self._lock = threading.Lock()

        self.stations_by_id: Dict[str, Station] = {}
        self.inventory_by_id: Dict[str, Dict[str, Availability]] = {}
        self._ui_min_year: int = 0

        # (-1.0, -1.0) bedeutet: noch nie geladen
        self._mtime_key: Tuple[float, float] = (-1.0, -1.0)

    def ensure_loaded(self) -> None:
        paths = self._ensure_paths()
        current_key = self._make_mtime_key(paths.stations, paths.inventory)

        # Dateien unverändert -> nichts tun
        if self._mtime_key == current_key:
            return

        # Dateien neu/anders -> unter Lock neu laden
        with self._lock:
            paths = self._ensure_paths()
            current_key = self._make_mtime_key(paths.stations, paths.inventory)
            if self._mtime_key == current_key:
                return

            self.stations_by_id = _parse_stations(paths.stations)
            self.inventory_by_id = _parse_inventory(paths.inventory)
            self._ui_min_year = _compute_ui_min_year(self.inventory_by_id)

            self._mtime_key = current_key

    def ui_min_year(self) -> int:
        self.ensure_loaded()
        return self._ui_min_year

    def _ensure_paths(self):
        try:
            return self.files.ensure()
        except Exception as e:
            raise DataUnavailableError(f"Failed to load metadata files: {str(e)}")

    @staticmethod
    def _make_mtime_key(stations_path: Path, inventory_path: Path) -> Tuple[float, float]:
        return (stations_path.stat().st_mtime, inventory_path.stat().st_mtime)


def _parse_stations(path: Path) -> Dict[str, Station]:
    # ID(0:11) LAT(12:20) LON(21:30) NAME(41:71)
    ID_SLICE = slice(0, 11)
    LAT_SLICE = slice(12, 20)
    LON_SLICE = slice(21, 30)
    NAME_SLICE = slice(41, 71)

    #Dict key stations_id, value Stationsobjekt
    stations: Dict[str, Station] = {}

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            station = _parse_station_line(line, ID_SLICE, LAT_SLICE, LON_SLICE, NAME_SLICE)
            if station is None:
                continue
            stations[station.stationId] = station

    return stations


def _parse_inventory(path: Path) -> Dict[str, Dict[str, Availability]]:
    # ID(0:11) ELEMENT(31:35) FIRSTYEAR(36:40) LASTYEAR(41:45)
    ID_SLICE = slice(0, 11)
    ELEMENT_SLICE = slice(31, 35)
    FIRSTYEAR_SLICE = slice(36, 40)
    LASTYEAR_SLICE = slice(41, 45)

    #Dict key stations_id, value Dict mit key Element (TMIN/TMAX) und 
    # value Availability(firstYear, lastYear)
    inv: Dict[str, Dict[str, Availability]] = {}

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            parsed = _parse_inventory_line(
                line, ID_SLICE, ELEMENT_SLICE, FIRSTYEAR_SLICE, LASTYEAR_SLICE
            )
            if parsed is None:
                continue
            station_id, element, first_year, last_year = parsed

            # 1) Station-Dict holen oder neu anlegen
            if station_id not in inv:
                inv[station_id] = {}

            station_inv = inv[station_id]

            # 2) Element setzen oder "Spanne erweitern"
            if element not in station_inv:
                station_inv[element] = Availability(firstYear=first_year, lastYear=last_year)
            else:
                prev = station_inv[element]
                station_inv[element] = Availability(
                    firstYear=min(prev.firstYear, first_year),
                    lastYear=max(prev.lastYear, last_year),
                )

    return inv


def _parse_station_line(
    line: str,
    id_slice: slice,
    lat_slice: slice,
    lon_slice: slice,
    name_slice: slice,
) -> Station | None:
    if len(line) < name_slice.stop:
        return None

    station_id = line[id_slice].strip()
    lat = float(line[lat_slice].strip())
    lon = float(line[lon_slice].strip())
    name = line[name_slice].strip()
    return Station(stationId=station_id, lat=lat, lon=lon, name=name)


def _parse_inventory_line(
    line: str,
    id_slice: slice,
    element_slice: slice,
    firstyear_slice: slice,
    lastyear_slice: slice,
) -> Tuple[str, str, int, int] | None:
    if len(line) < lastyear_slice.stop:
        return None

    element = line[element_slice].strip()
    if element not in ("TMIN", "TMAX"):
        return None

    station_id = line[id_slice].strip()
    first_year = int(line[firstyear_slice].strip())
    last_year = int(line[lastyear_slice].strip())
    return station_id, element, first_year, last_year


def _compute_ui_min_year(inv_by_id: Dict[str, Dict[str, Availability]]) -> int:
    # Ohne Optional/None: wir starten mit "sehr groß" und merken uns, ob wir etwas gefunden haben
    found_tmin = False
    found_tmax = False
    min_tmin = 10**9
    min_tmax = 10**9

    for m in inv_by_id.values():
        if "TMIN" in m:
            found_tmin = True
            min_tmin = min(min_tmin, m["TMIN"].firstYear)
        if "TMAX" in m:
            found_tmax = True
            min_tmax = min(min_tmax, m["TMAX"].firstYear)

    if not found_tmin and not found_tmax:
        return 0
    if not found_tmin:
        return int(min_tmax)
    if not found_tmax:
        return int(min_tmin)

    return int(max(min_tmin, min_tmax))