from __future__ import annotations
from pathlib import Path
from app.data.http_cache import HttpCache

AWS_BASE = "https://noaa-ghcn-pds.s3.amazonaws.com"
BY_STATION_URL = f"{AWS_BASE}/csv.gz/by_station/{{station_id}}.csv.gz"

class NoaaStationFiles:
    def __init__(self, http: HttpCache, cache_dir: Path, station_ttl_seconds: int):
        self.http = http
        self.cache_dir = cache_dir
        self.station_ttl_seconds = station_ttl_seconds

    def ensure_station_gz(self, station_id: str) -> Path:
        #Pfad bauen:z.B. /cache/stations/by_station/USW00094728.csv.gz
        path = self.cache_dir / "stations" / "by_station" / f"{station_id}.csv.gz"
        url = BY_STATION_URL.format(station_id=station_id)
        self.http.get_to_file(url, path, max_age_seconds=self.station_ttl_seconds)
        return path
