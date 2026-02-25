from pydantic import BaseModel
import os

from app.constants.config import (
    CACHE_DIR_DEFAULT,
    META_DATA_TTL_SEC_DEFAULT,
    STATION_TTL_SEC_DEFAULT,
    HTTP_TIMEOUT_SEC_DEFAULT,
)

class Settings(BaseModel):
    # ENV wird aus dem Container gelesen; sonst gelten Defaults.
    cache_dir: str = os.getenv("CACHE_DIR", CACHE_DIR_DEFAULT)

    meta_data_ttl_sec: int = int(os.getenv("META_DATA_TTL_SEC", str(META_DATA_TTL_SEC_DEFAULT)))
    station_ttl_sec: int = int(os.getenv("STATION_TTL_SEC", str(STATION_TTL_SEC_DEFAULT)))
    http_timeout_sec: int = int(os.getenv("HTTP_TIMEOUT_SEC", str(HTTP_TIMEOUT_SEC_DEFAULT)))

settings = Settings()
