from fastapi import APIRouter, Query, Request, HTTPException
from datetime import date

from app.api.schemas import (
    HealthResponse,
    MetaResponse,
    UiLimits,
    StationsNearbyResponse,
    StationResult,
    StationAvailability,
    StationTemperatureSeriesResponse,
)
from app.api.validation import validate_year_range

router = APIRouter(prefix="/api")

@router.get("/health", response_model=HealthResponse)
def health(request: Request):
    metadata_store = request.app.state.metadata_store
    return HealthResponse(status="ok")

@router.get("/meta", response_model=MetaResponse)
def meta(request: Request):
    metadata_store = request.app.state.metadata_store
    min_year = metadata_store.ui_min_year()
    max_year = date.today().year - 1
    return MetaResponse(ui=UiLimits(minYear=min_year, maxYear=max_year))

@router.get("/stations/nearby", response_model=StationsNearbyResponse)
def stations_nearby(
    request: Request,
    lat: float,
    lon: float,
    radiusKm: int = Query(50, ge=1, le=100),
    limit: int = Query(10, ge=1, le=10),
    startYear: int = Query(...),
    endYear: int = Query(...),
):
    metadata_store = request.app.state.metadata_store
    station_search = request.app.state.station_search

    min_year = metadata_store.ui_min_year()
    max_year = date.today().year - 1
    validate_year_range(startYear, endYear, min_year=min_year, max_year=max_year)

    candidates = station_search.find_nearby(
        lat=lat, lon=lon,
        radius_km=radiusKm,
        limit=limit,
        start_year=startYear,
        end_year=endYear,
    )

    results = []
    for c in candidates:
        availability = {
            k: StationAvailability(firstYear=v.firstYear, lastYear=v.lastYear)
            for k, v in c.availability.items()
        }
        results.append(StationResult(
            stationId=c.stationId,
            name=c.name,
            lat=c.lat,
            lon=c.lon,
            distanceKm=c.distanceKm,
            availability=availability,
        ))

    return StationsNearbyResponse(results=results)

@router.get("/stations/{stationId}/series", response_model=StationTemperatureSeriesResponse)
def station_series(
    request: Request,
    stationId: str,
    startYear: int = Query(...),
    endYear: int = Query(...),
):
    metadata_store = request.app.state.metadata_store
    series_service = request.app.state.series_service

    min_year = metadata_store.ui_min_year()
    max_year = date.today().year - 1
    validate_year_range(startYear, endYear, min_year=min_year, max_year=max_year)

    try:
        years, series = series_service.compute_temperature_series(
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
