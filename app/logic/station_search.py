from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from operator import attrgetter

from app.logic.geo import bounding_box, haversine_km
from app.logic.metadata_store import MetadataStore
from app.models.station import Availability
from app.constants.temperature_constants import ELEMENTS


@dataclass(frozen=True)
class StationCandidate:
    stationId: str
    name: Optional[str]
    lat: float
    lon: float
    distanceKm: float
    availability: Availability  


def _passes_year_filter(first: int, last: int, start_year: int, end_year: int) -> bool:
    return first <= start_year and last >= end_year


class StationSearchService:
    def __init__(self, metadata: MetadataStore):
        self.metadata = metadata

    def find_nearby(
        self,
        lat: float,
        lon: float,
        radius_km: int,
        limit: int,
        start_year: int,
        end_year: int,
    ) -> List[StationCandidate]:
        self.metadata.ensure_loaded()

        # Bounding Box gibt Tuple (minLat, maxLat, minLon, maxLon) zurück
        min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius_km)
        candidates: List[StationCandidate] = []

        for station in self.metadata.stations_by_id.values():
            if not self._is_within_bbox(station, min_lat, max_lat, min_lon, max_lon):
                continue

            dist = self._distance_km(lat, lon, station)
            if not self._is_within_radius(dist, radius_km):
                continue

            availability = self._get_overlap_availability(
                station_id=station.stationId,
                start_year=start_year,
                end_year=end_year,
            )
            if availability is None:
                continue

            candidates.append(
                StationCandidate(
                    stationId=station.stationId,
                    name=station.name,
                    lat=station.lat,
                    lon=station.lon,
                    distanceKm=round(dist, 3),
                    availability=availability,
                )
            )

        candidates.sort(key=attrgetter("distanceKm"))
        return candidates[:limit]

    @staticmethod
    def _is_within_bbox(station: "Station", min_lat: float, max_lat: float, min_lon: float, max_lon: float) -> bool:
        return min_lat <= station.lat <= max_lat and min_lon <= station.lon <= max_lon

    @staticmethod
    def _distance_km(lat: float, lon: float, station: "Station") -> float:
        return haversine_km(lat, lon, station.lat, station.lon)

    @staticmethod
    def _is_within_radius(distance_km: float, radius_km: int) -> bool:
        return distance_km <= radius_km

    def _get_overlap_availability(
        self,
        station_id: str,
        start_year: int,
        end_year: int,
    ) -> Optional[Availability]:
        inv = self.metadata.inventory_by_id.get(station_id, {})

        tmin = inv.get("TMIN")
        tmax = inv.get("TMAX")
        if tmin is None or tmax is None:
            return None
        if not _passes_year_filter(tmin.firstYear, tmin.lastYear, start_year, end_year):
            return None
        if not _passes_year_filter(tmax.firstYear, tmax.lastYear, start_year, end_year):
            return None

        first_year = max(tmin.firstYear, tmax.firstYear)
        last_year = min(tmin.lastYear, tmax.lastYear)
        if first_year > last_year:
            return None

        return Availability(firstYear=first_year, lastYear=last_year)