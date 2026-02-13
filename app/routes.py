from fastapi import APIRouter, Query
from app.schemas import HealthResponse, MetaResponse, UiLimits, StationsNearbyResponse
from app.services.station_service import find_nearby_stations

router = APIRouter(prefix="/api")

@router.get("/health", response_model=HealthResponse, summary="Healthcheck")
def health():
    return HealthResponse(status="ok")


@router.get("/meta", response_model=MetaResponse, summary="UI limits and metadata")
def meta():
    ui = UiLimits(
        minYear=get_ui_min_year(),
        maxYear=get_ui_max_year(),
    )
    return MetaResponse(ui=ui)


@router.get(
    "/stations/nearby",
    response_model=StationsNearbyResponse,
    summary="Find nearby stations within radius",
)
def stations_nearby(
    lat: float,
    lon: float,
    radiusKm: int = Query(50, ge=1, le=100),
    limit: int = Query(10, ge=1, le=10),
    startYear: int = Query(..., ge=1700, le=2100),
    endYear: int = Query(..., ge=1700, le=2100),
    requireElements: str | None = Query(None, description="Elements separated by ';' e.g. TMIN;TMAX"),
    mode: str = Query("strict", pattern="^(strict|either)$"),
):
    require_list = requireElements.split(";") if requireElements else None

    results = find_nearby_stations(
        lat=lat,
        lon=lon,
        radius_km=radiusKm,
        limit=limit,
        start_year=startYear,
        end_year=endYear,
        require_elements=require_list,
        mode=mode,
    )
    return StationsNearbyResponse(results=results)