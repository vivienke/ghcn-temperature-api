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
        metadata_paths = self._metadata_paths()

        self._ensure_file(STATIONS_URL, metadata_paths.stations, self.meta_ttl_seconds)
        self._ensure_file(INVENTORY_URL, metadata_paths.inventory, self.meta_ttl_seconds)

        return metadata_paths

    def _metadata_paths(self) -> MetadataPaths:
        metadata_dir = self.cache_dir / "meta"
        stations_path = metadata_dir / "ghcnd-stations.txt"
        inventory_path = metadata_dir / "ghcnd-inventory.txt"
        return MetadataPaths(stations=stations_path, inventory=inventory_path)

    def _ensure_file(
        self,
        url: str,
        dest_path: Path,
        ttl_seconds: int | None,
    ) -> None:
        self.http.fetch_to_file(url, dest_path, ttl_seconds=ttl_seconds)
