from typing import Dict, List, Optional

from pydantic import BaseModel


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
    name: str
    lat: float
    lon: float
    distanceKm: float
    availability: StationAvailability


class StationsNearbyResponse(BaseModel):
    results: List[StationResult]


class StationTemperatureSeriesResponse(BaseModel):
    stationId: str
    startYear: int
    endYear: int
    years: List[int]
    #durch Optional null-Werte erlauben,falls Datenlücken vorhanden sind
    series: Dict[str, List[Optional[float]]]
