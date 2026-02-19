from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict
import threading

from app.services.meta_service import ensure_metadata


@dataclass(frozen=True)
class Station:
    stationId: str
    lat: float
    lon: float
    name: str


@dataclass(frozen=True)
class Availability:
    firstYear: int
    lastYear: int


class MetadataStore:
    """
    Lazy-load + In-Memory Cache für Stations + Inventory.
    Aktualisiert täglich, wenn ensure_metadata neue Dateien geladen hat.
    """
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded = False
        self._loaded_on: str | None = None

        self.stations_by_id: Dict[str, Station] = {}
        self.inventory_by_id: Dict[str, Dict[str, Availability]] = {}

    def ensure_loaded(self, cache_dir: str) -> None:
        paths = ensure_metadata(cache_dir)

        # Wenn bereits geladen und Datum gleich, nichts tun
        if self._loaded and self._loaded_on == paths.refreshedOn:
            return

        with self._lock:
            # Doppelte Prüfung nach Lock
            paths = ensure_metadata(cache_dir)
            if self._loaded and self._loaded_on == paths.refreshedOn:
                return

            self.stations_by_id = _parse_stations(paths.stations)
            self.inventory_by_id = _parse_inventory(paths.inventory)

            self._loaded = True
            self._loaded_on = paths.refreshedOn


def _parse_stations(path: Path) -> Dict[str, Station]:
    # Fixed-width Format:
    # ID(11) LAT(9) LON(10) ELEV(7) STATE(3) NAME(30) ...
    stations: Dict[str, Station] = {}
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(line) < 71:
                continue
            station_id = line[0:11].strip()
            lat = float(line[12:20].strip())
            lon = float(line[21:30].strip())
            name = line[41:71].strip()
            stations[station_id] = Station(stationId=station_id, lat=lat, lon=lon, name=name)
    return stations


def _parse_inventory(path: Path) -> Dict[str, Dict[str, Availability]]:
    # Fixed-width Format:
    # ID(11) LAT(9) LON(10) ELEMENT(4) FIRSTYEAR(4) LASTYEAR(4)
    inv: Dict[str, Dict[str, Availability]] = {}

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(line) < 45:
                continue

            station_id = line[0:11].strip()
            element = line[31:35].strip()
            if element not in ("TMIN", "TMAX"):
                continue

            first_year = int(line[36:40].strip())
            last_year = int(line[41:45].strip())

            station_map = inv.setdefault(station_id, {})
            existing = station_map.get(element)

            # Merge, falls es mehrere Einträge pro stationId/element gibt
            if existing is None:
                station_map[element] = Availability(firstYear=first_year, lastYear=last_year)
            else:
                station_map[element] = Availability(
                    firstYear=min(existing.firstYear, first_year),
                    lastYear=max(existing.lastYear, last_year),
                )

    return inv


metadata_store = MetadataStore()
