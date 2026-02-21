from pydantic import BaseModel
import os

class Settings(BaseModel):
    # ENV wird aus dem Container gelesen; sonst gelten Defaults.
    cache_dir: str = os.getenv("CACHE_DIR", "/cache")

    meta_data_ttl_sec: int = int(os.getenv("META_DATA_TTL_SEC", str(7 * 24 * 3600)))
    station_ttl_sec: int = int(os.getenv("STATION_TTL_SEC", str(30 * 24 * 3600)))
    http_timeout_sec: int = int(os.getenv("HTTP_TIMEOUT_SEC", str(60)))

settings = Settings()
