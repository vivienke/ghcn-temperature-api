import os
from fastapi import APIRouter, Query, HTTPException

from app.schemas import (
    HealthResponse,
    MetaResponse,
    UiLimits,
    StationsNearbyResponse,
    StationTemperatureSeriesResponse,
)
from app.services.meta_service import get_ui_min_year, get_ui_max_year
from app.services.station_service import find_nearby_stations
from app.services.series_service import compute_temperature_series

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


@router.get("/meta", response_model=MetaResponse)
def meta():
    cache_dir = os.getenv("CACHE_DIR", "/cache")
    ui = UiLimits(
        minYear=get_ui_min_year(cache_dir),
        maxYear=get_ui_max_year(),
    )
    return MetaResponse(ui=ui)


@router.get("/stations/nearby", response_model=StationsNearbyResponse)
def stations_nearby(
    lat: float,
    lon: float,
    radiusKm: int = Query(50, ge=1, le=100),
    limit: int = Query(10, ge=1, le=10),
    startYear: int = Query(...),
    endYear: int = Query(...),
):
    cache_dir = os.getenv("CACHE_DIR", "/cache")

    min_year = get_ui_min_year(cache_dir)
    max_year = get_ui_max_year()

    if startYear > endYear:
        raise HTTPException(400, f"Invalid year range: startYear ({startYear}) must be <= endYear ({endYear}).")
    if endYear > max_year:
        raise HTTPException(400, f"Invalid endYear ({endYear}). Max allowed is {max_year} (previous year).")
    if startYear < min_year:
        raise HTTPException(400, f"Invalid startYear ({startYear}). Min allowed is {min_year} (derived from data).")

    results = find_nearby_stations(
        lat=lat,
        lon=lon,
        radius_km=radiusKm,
        limit=limit,
        start_year=startYear,
        end_year=endYear,
        cache_dir=cache_dir,
    )
    return StationsNearbyResponse(results=results)


@router.get("/stations/{stationId}/series", response_model=StationTemperatureSeriesResponse)
def station_series(
    stationId: str,
    startYear: int = Query(...),
    endYear: int = Query(...),
):
    cache_dir = os.getenv("CACHE_DIR", "/cache")

    min_year = get_ui_min_year(cache_dir)
    max_year = get_ui_max_year()

    if startYear > endYear:
        raise HTTPException(400, f"Invalid year range: startYear ({startYear}) must be <= endYear ({endYear}).")
    if endYear > max_year:
        raise HTTPException(400, f"Invalid endYear ({endYear}). Max allowed is {max_year} (previous year).")
    if startYear < min_year:
        raise HTTPException(400, f"Invalid startYear ({startYear}). Min allowed is {min_year} (derived from data).")

    try:
        years, series = compute_temperature_series(
            cache_dir=cache_dir,
            station_id=stationId,
            start_year=startYear,
            end_year=endYear,
            ignore_qflag=True,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Station '{stationId}' not found.")

    return StationTemperatureSeriesResponse(
        stationId=stationId,
        startYear=startYear,
        endYear=endYear,
        years=years,
        series=series,
    )
