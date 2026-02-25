from fastapi import APIRouter, Query, Request, HTTPException
from datetime import date
import asyncio

from app.api.schemas import (
    HealthResponse,
    MetaResponse,
    UiLimits,
    StationsNearbyResponse,
    StationTemperatureSeriesResponse,
)
from app.core.exceptions import StationNotFoundError, DataUnavailableError
from app.api.helpers import _validate_years, _to_station_result

router = APIRouter(prefix="/api")

@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    return HealthResponse(status="ok")

@router.get("/meta", response_model=MetaResponse)
async def meta(request: Request):
    metadata_store = request.app.state.metadata_store
    min_year = metadata_store.ui_min_year()
    max_year = date.today().year - 1
    return MetaResponse(ui=UiLimits(minYear=min_year, maxYear=max_year))

@router.get("/stations/nearby", response_model=StationsNearbyResponse)
async def stations_nearby(
    request: Request,
    lat: float,
    lon: float,
    radiusKm: int = Query(50, ge=1, le=100),
    limit: int = Query(10, ge=1, le=10),
    startYear: int = Query(...),
    endYear: int = Query(...),
):
    station_search = request.app.state.station_search

    await _validate_years(request, startYear, endYear)

    try:
        candidates = await asyncio.to_thread(
            station_search.find_nearby,
            lat=lat,
            lon=lon,
            radius_km=radiusKm,
            limit=limit,
            start_year=startYear,
            end_year=endYear,
        )
    except DataUnavailableError as e:
        raise HTTPException(status_code=503, detail=f"Service temporarily unavailable: {str(e)}")

    results = [_to_station_result(candidate) for candidate in candidates]

    return StationsNearbyResponse(results=results)


@router.get("/stations/{stationId}/series", response_model=StationTemperatureSeriesResponse)
async def station_series(
    request: Request,
    stationId: str,
    startYear: int = Query(...),
    endYear: int = Query(...),
):
    series_service = request.app.state.series_service

    await _validate_years(request, startYear, endYear)

    try:
        years, series = await asyncio.to_thread(
            series_service.compute_temperature_series,
            station_id=stationId,
            start_year=startYear,
            end_year=endYear,
            ignore_qflag=True,
        )
    except StationNotFoundError:
        raise HTTPException(status_code=404, detail=f"Station '{stationId}' not found.")
    except DataUnavailableError as e:
        raise HTTPException(status_code=503, detail=f"Service temporarily unavailable: {str(e)}")

    return StationTemperatureSeriesResponse(
        stationId=stationId,
        startYear=startYear,
        endYear=endYear,
        years=years,
        series=series,
    )
