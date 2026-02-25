from fastapi import HTTPException
from datetime import date
import asyncio

from app.api.validation import validate_year_range
from app.api.schemas import StationAvailability, StationResult
from app.core.exceptions import InvalidYearRangeError
from app.logic.station_search import StationCandidate


async def _validate_years(request, start_year: int, end_year: int) -> None:
    metadata_store = request.app.state.metadata_store
    min_year = metadata_store.ui_min_year()
    max_year = date.today().year - 1
    try:
        await asyncio.to_thread(
            validate_year_range, start_year, end_year, min_year=min_year, max_year=max_year
        )
    except InvalidYearRangeError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _to_station_result(candidate: StationCandidate) -> StationResult:
    station_availability = StationAvailability(
        firstYear=candidate.availability.firstYear,
        lastYear=candidate.availability.lastYear,
    )
    return StationResult(
        stationId=candidate.stationId,
        name=candidate.name,
        lat=candidate.lat,
        lon=candidate.lon,
        distanceKm=candidate.distanceKm,
        availability=station_availability,
    )