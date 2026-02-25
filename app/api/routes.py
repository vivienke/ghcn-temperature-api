import asyncio
from fastapi import APIRouter, Query, Request, HTTPException
from datetime import date

from app.api.schemas import (
    HealthResponse,
    MetaResponse,
    StationAvailability,
    StationResult,
    UiLimits,
    StationsNearbyResponse,
    StationTemperatureSeriesResponse,
)
from app.exceptions import DataUnavailableError, StationNotFoundError
from app.api.validation import validate_years_or_raise_http_400

router = APIRouter(prefix="/api")

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")

@router.get("/meta", response_model=MetaResponse)
async def meta(request: Request):
    metadata_store = request.app.state.metadata_store
    min_year = metadata_store.ui_min_year()
    max_year = date.today().year - 1
    return MetaResponse(
        ui=UiLimits(
            minYear=min_year,
            maxYear=max_year,
            radiusKmMin=1,
            radiusKmMax=100,
            limitMin=1,
            limitMax=10,
        )
    )

@router.get("/stations/nearby", response_model=StationsNearbyResponse)
async def stations_nearby(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radiusKm: int = Query(50, ge=1, le=100),
    limit: int = Query(10, ge=1, le=10),
    startYear: int = Query(...),
    endYear: int = Query(...),
):
    station_search = request.app.state.station_search

    await validate_years_or_raise_http_400(request, startYear, endYear)

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

    # Kandidaten aus der Logik-Schicht in API-Response-Objekte umwandeln
    results = [
        StationResult(
            stationId=candidate.stationId,
            name=candidate.name,
            lat=candidate.lat,
            lon=candidate.lon,
            distanceKm=candidate.distanceKm,
            availability=StationAvailability(
                firstYear=candidate.availability.firstYear,
                lastYear=candidate.availability.lastYear,
            ),
        )
        for candidate in candidates
    ]

    return StationsNearbyResponse(results=results)


@router.get("/stations/{stationId}/series", response_model=StationTemperatureSeriesResponse)
async def station_series(
    request: Request,
    stationId: str,
    startYear: int = Query(...),
    endYear: int = Query(...),
):
    series_service = request.app.state.series_service

    await validate_years_or_raise_http_400(request, startYear, endYear)

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
