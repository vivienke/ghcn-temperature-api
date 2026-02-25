from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Station:
    stationId: str
    lat: float
    lon: float
    name: str


@dataclass(frozen=True)
class Availability:
    firstYear: int
    lastYear: int
