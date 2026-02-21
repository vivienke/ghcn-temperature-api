from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from app.data.http_cache import HttpCache

AWS_BASE = "https://noaa-ghcn-pds.s3.amazonaws.com"
STATIONS_URL = f"{AWS_BASE}/ghcnd-stations.txt"
INVENTORY_URL = f"{AWS_BASE}/ghcnd-inventory.txt"

@dataclass(frozen=True)
class MetadataPaths:
    stations: Path
    inventory: Path

class NoaaMetadataFiles:
    def __init__(self, http: HttpCache, cache_dir: Path, meta_ttl_seconds: int):
        self.http = http
        self.cache_dir = cache_dir
        self.meta_ttl_seconds = meta_ttl_seconds

    def ensure(self) -> MetadataPaths:
        meta_dir = self.cache_dir / "meta"
        stations = meta_dir / "ghcnd-stations.txt"
        inventory = meta_dir / "ghcnd-inventory.txt"

        self.http.get_to_file(STATIONS_URL, stations, max_age_seconds=self.meta_ttl_seconds)
        self.http.get_to_file(INVENTORY_URL, inventory, max_age_seconds=self.meta_ttl_seconds)

        # safety fallback (z.B. first run)
        if not stations.exists():
            self.http.get_to_file(STATIONS_URL, stations, max_age_seconds=None)
        if not inventory.exists():
            self.http.get_to_file(INVENTORY_URL, inventory, max_age_seconds=None)

        return MetadataPaths(stations=stations, inventory=inventory)
