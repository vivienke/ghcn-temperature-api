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
        paths = self._metadata_paths()

        self._ensure_file(STATIONS_URL, paths.stations, self.meta_ttl_seconds)
        self._ensure_file(INVENTORY_URL, paths.inventory, self.meta_ttl_seconds)

        # safety fallback (z.B. first run)
        self._ensure_file(STATIONS_URL, paths.stations, None, require_exists=True)
        self._ensure_file(INVENTORY_URL, paths.inventory, None, require_exists=True)

        return paths

    def _metadata_paths(self) -> MetadataPaths:
        metadata_dir = self.cache_dir / "meta"
        stations_path = metadata_dir / "ghcnd-stations.txt"
        inventory_path = metadata_dir / "ghcnd-inventory.txt"
        return MetadataPaths(stations=stations_path, inventory=inventory_path)

    def _ensure_file(
        self,
        url: str,
        path: Path,
        max_age_seconds: int | None,
        require_exists: bool = False,
    ) -> None:
        if require_exists and path.exists():
            return
        self.http.get_to_file(url, path, max_age_seconds=max_age_seconds)
