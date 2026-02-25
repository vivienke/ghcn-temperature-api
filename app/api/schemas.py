from pydantic import BaseModel
from typing import Dict, List, Optional, Literal

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
    availability: Optional[StationAvailability] = None  # <- vereinheitlicht

class StationsNearbyResponse(BaseModel):
    results: List[StationResult]

PeriodKey = Literal["YEAR", "SPRING", "SUMMER", "AUTUMN", "WINTER"]
ElementKey = Literal["TMIN", "TMAX"]
SeriesKey = str  # "<PERIOD>_<ELEMENT>"

class StationTemperatureSeriesResponse(BaseModel):
    stationId: str
    startYear: int
    endYear: int
    years: List[int]
    series: Dict[SeriesKey, List[Optional[float]]]
