from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple
import threading

from app.data.noaa_metadata_files import NoaaMetadataFiles
from app.models.station import Station, Availability
from app.exceptions.data import DataUnavailableError


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
        try:
            paths = self.files.ensure()
        except Exception as e:
            raise DataUnavailableError(f"Failed to load metadata files: {str(e)}")
        current_key = self._make_mtime_key(paths.stations, paths.inventory)

        # Dateien unverändert -> nichts tun
        if self._mtime_key == current_key:
            return

        # Dateien neu/anders -> unter Lock neu laden
        with self._lock:
            try:
                paths = self.files.ensure()
            except Exception as e:
                raise DataUnavailableError(f"Failed to load metadata files: {str(e)}")
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
            if len(line) < NAME_SLICE.stop:
                continue

            station_id = line[ID_SLICE].strip()
            lat = float(line[LAT_SLICE].strip())
            lon = float(line[LON_SLICE].strip())
            name = line[NAME_SLICE].strip()

            stations[station_id] = Station(stationId=station_id, lat=lat, lon=lon, name=name)

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
            if len(line) < LASTYEAR_SLICE.stop:
                continue

            element = line[ELEMENT_SLICE].strip()
            if element not in ("TMIN", "TMAX"):
                continue

            station_id = line[ID_SLICE].strip()
            first_year = int(line[FIRSTYEAR_SLICE].strip())
            last_year = int(line[LASTYEAR_SLICE].strip())

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