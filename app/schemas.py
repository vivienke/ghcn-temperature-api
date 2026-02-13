from pydantic import BaseModel
from typing import List, Optional

class HealthResponse(BaseModel):
    status: str

class UiLimits(BaseModel):
    minYear: int
    maxYear: int
    radiusKmMin: int = 1
    radiusKmMax: int = 100
    limitMin: int = 1
    limitMax: int = 10

class MetaResponse(BaseModel):
    ui: UiLimits


class StationAvailability(BaseModel):
    firstYear: int
    lastYear: int


class StationResult(BaseModel):
    stationId: str
    name: Optional[str] = None
    lat: float
    lon: float
    distanceKm: float
    availability: Optional[dict[str, StationAvailability]] = None

class StationsNearbyResponse(BaseModel):
    results: List[StationResult]