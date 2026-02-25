from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import List

from app.data.http_cache import HttpCache

AWS_BASE = "https://noaa-ghcn-pds.s3.amazonaws.com"
BY_STATION_URL = f"{AWS_BASE}/csv.gz/by_station/{{station_id}}.csv.gz"


class NoaaStationFiles:
    def __init__(
        self,
        http: HttpCache,
        cache_dir: Path,
        station_ttl_seconds: int,
        cache_limit: int = 5,
    ):
        self.http = http
        self.cache_dir = cache_dir
        self.station_ttl_seconds = station_ttl_seconds
        self.cache_limit = cache_limit

        # Schützt den gemeinsamen Cache-Status bei parallelen Requests.
        self._lock = threading.Lock()
        self._state_path = self.cache_dir / "stations" / "by_station" / "state.json"

    def ensure_station_gz(self, station_id: str) -> Path:
        station_cache_dir = self._station_dir()
        station_path = self._station_path(station_cache_dir, station_id)
        station_url = self._station_url(station_id)

        self.http.fetch_to_file(station_url, station_path, ttl_seconds=self.station_ttl_seconds)

        # Cache-Limit anwenden (auch wenn nur "genutzt", nicht nur "heruntergeladen")
        if self.cache_limit > 0:
            self._update_cache_state(station_cache_dir, station_id)

        return station_path

    def _station_dir(self) -> Path:
        return self.cache_dir / "stations" / "by_station"

    @staticmethod
    def _station_path(station_cache_dir: Path, station_id: str) -> Path:
        return station_cache_dir / f"{station_id}.csv.gz"

    @staticmethod
    def _station_url(station_id: str) -> str:
        return BY_STATION_URL.format(station_id=station_id)

    def _update_cache_state(self, station_cache_dir: Path, station_id: str) -> None:
        with self._lock:
            order = self._load_state(station_cache_dir)
            self._touch(order, station_id)
            self._evict_if_needed(order, station_cache_dir)
            self._save_state(order, station_cache_dir)

    # -----------------------
    # Statusverwaltung (persistiert im Volume)
    # -----------------------

    def _load_state(self, station_cache_dir: Path) -> List[str]:
        station_cache_dir.mkdir(parents=True, exist_ok=True)

        if not self._state_path.exists():
            # Wenn kein Status vorhanden ist: aus Dateien bestmöglich rekonstruieren
            return self._rebuild_order_from_files(station_cache_dir)

        try:
            state_data = json.loads(self._state_path.read_text(encoding="utf-8"))
            station_order = state_data.get("order", [])
            if not isinstance(station_order, list):
                station_order = []
            # nur strings behalten
            station_order = [x for x in station_order if isinstance(x, str) and x]
            return station_order
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return self._rebuild_order_from_files(station_cache_dir)

    def _save_state(self, order: List[str], station_cache_dir: Path) -> None:
        station_cache_dir.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps({"order": order}, indent=2), encoding="utf-8")

    def _rebuild_order_from_files(self, station_cache_dir: Path) -> List[str]:
        # Rekonstruktion: sortiere nach mtime (älteste zuerst)
        files = [p for p in station_cache_dir.glob("*.csv.gz") if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime)
        return [
            p.name[:-len(".csv.gz")]
            for p in files
            if p.name.endswith(".csv.gz")
        ]

    # -----------------------
    # LRU-ähnlich: "zuletzt genutzt" ans Ende schieben
    # -----------------------

    def _touch(self, order: List[str], station_id: str) -> None:
        if station_id in order:
            order.remove(station_id)
        order.append(station_id)

    def _evict_if_needed(self, order: List[str], station_cache_dir: Path) -> None:
        while len(order) > self.cache_limit:
            oldest = order.pop(0)
            file_path = station_cache_dir / f"{oldest}.csv.gz"
            try:
                if file_path.exists():
                    file_path.unlink()
            except OSError:
                # Wenn Löschen fehlschlägt, ignorieren – Status ist trotzdem aktualisiert
                pass