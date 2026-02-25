from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List

from app.data.http_cache import HttpCache

AWS_BASE = "https://noaa-ghcn-pds.s3.amazonaws.com"
BY_STATION_URL = f"{AWS_BASE}/csv.gz/by_station/{{station_id}}.csv.gz"


@dataclass(frozen=True)
class StationCacheState:
    # Reihenfolge: älteste zuerst, neueste zuletzt
    order: List[str]


class NoaaStationFiles:
    def __init__(
        self,
        http: HttpCache,
        cache_dir: Path,
        station_ttl_seconds: int,
        cache_limit: int = 5,  # <- nur die letzten 5 Stationen behalten
    ):
        self.http = http
        self.cache_dir = cache_dir
        self.station_ttl_seconds = station_ttl_seconds
        self.cache_limit = cache_limit

        self._lock = threading.Lock()
        self._state_path = self.cache_dir / "stations" / "by_station" / "state.json"

    def ensure_station_gz(self, station_id: str) -> Path:
        by_station_dir = self._station_dir()
        station_path = self._station_path(by_station_dir, station_id)
        station_url = self._station_url(station_id)

        self.http.get_to_file(station_url, station_path, max_age_seconds=self.station_ttl_seconds)

        # Cachelimit anwenden (auch wenn nur "genutzt", nicht nur "downloaded")
        if self.cache_limit > 0:
            self._update_cache_state(by_station_dir, station_id)

            return station_path

    def _station_dir(self) -> Path:
        return self.cache_dir / "stations" / "by_station"

    @staticmethod
    def _station_path(by_station_dir: Path, station_id: str) -> Path:
        return by_station_dir / f"{station_id}.csv.gz"

    @staticmethod
    def _station_url(station_id: str) -> str:
        return BY_STATION_URL.format(station_id=station_id)

    def _update_cache_state(self, by_station_dir: Path, station_id: str) -> None:
        with self._lock:
            cache_state = self._load_state(by_station_dir)
            self._touch(cache_state, station_id)
            self._evict_if_needed(cache_state, by_station_dir)
            self._save_state(cache_state, by_station_dir)

    # -----------------------
    # State Handling (persistiert im Volume)
    # -----------------------

    def _load_state(self, by_station_dir: Path) -> StationCacheState:
        by_station_dir.mkdir(parents=True, exist_ok=True)

        if not self._state_path.exists():
            # Wenn kein state vorhanden ist: aus Dateien "best effort" rekonstruieren
            order = self._rebuild_order_from_files(by_station_dir)
            return StationCacheState(order=order)

        try:
            state_data = json.loads(self._state_path.read_text(encoding="utf-8"))
            station_order = state_data.get("order", [])
            if not isinstance(station_order, list):
                station_order = []
            # nur strings behalten
            station_order = [x for x in station_order if isinstance(x, str) and x]
            return StationCacheState(order=station_order)
        except Exception:
            order = self._rebuild_order_from_files(by_station_dir)
            return StationCacheState(order=order)

    def _save_state(self, state: StationCacheState, by_station_dir: Path) -> None:
        by_station_dir.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps({"order": state.order}, indent=2), encoding="utf-8")

    def _rebuild_order_from_files(self, by_station_dir: Path) -> List[str]:
        # Rekonstruktion: sortiere nach mtime (älteste zuerst)
        files = [p for p in by_station_dir.glob("*.csv.gz") if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime)
        return [p.stem for p in files]  # stem = station_id

    # -----------------------
    # LRU-ähnlich: "zuletzt genutzt" ans Ende schieben
    # -----------------------

    def _touch(self, state: StationCacheState, station_id: str) -> None:
        if station_id in state.order:
            state.order.remove(station_id)
        state.order.append(station_id)

    def _evict_if_needed(self, state: StationCacheState, by_station_dir: Path) -> None:
        while len(state.order) > self.cache_limit:
            oldest = state.order.pop(0)
            file_path = by_station_dir / f"{oldest}.csv.gz"
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                # Wenn löschen nicht klappt, ignorieren – state ist trotzdem aktualisiert
                pass