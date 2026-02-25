from fastapi import FastAPI
from pathlib import Path
import logging

from app.config import settings
from app.util.timing import RequestTimingMiddleware

from app.data.http_cache import HttpCache
from app.data.noaa_metadata_files import NoaaMetadataFiles
from app.data.noaa_station_files import NoaaStationFiles

from app.logic.metadata_store import MetadataStore
from app.logic.station_search import StationSearchService
from app.logic.temperature_series import TemperatureSeriesService


def create_app() -> FastAPI:
    app = FastAPI(title="GHCN Temperature API")

    # logging basic (optional)
    logging.basicConfig(level=logging.WARNING)

    http = HttpCache(timeout_sec=settings.http_timeout_sec)

    cache_dir = Path(settings.cache_dir)

    meta_files = NoaaMetadataFiles(
        http=http,
        cache_dir=cache_dir,
        meta_ttl_seconds=settings.meta_data_ttl_sec,
        )
    station_files = NoaaStationFiles(
    http=http,
    cache_dir=cache_dir,
    station_ttl_seconds=settings.station_ttl_sec,
    cache_limit=5, 
)
    metadata_store = MetadataStore(files=meta_files)
    station_search = StationSearchService(metadata=metadata_store)
    series_service = TemperatureSeriesService(
        metadata=metadata_store, station_files=station_files
    )

    app.state.metadata_store = metadata_store
    app.state.station_search = station_search
    app.state.series_service = series_service

    app.add_middleware(RequestTimingMiddleware)

    from app.api.routes import router

    app.include_router(router)

    @app.on_event("startup")
    def warmup():
        # Warmup: Metadaten laden/parsen
        metadata_store.ensure_loaded()

    return app


app = create_app()
