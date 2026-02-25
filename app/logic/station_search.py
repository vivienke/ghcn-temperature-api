from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from operator import attrgetter

from app.logic.geo import bounding_box, haversine_km
from app.logic.metadata_store import MetadataStore, Availability

REQUIRED_ELEMENTS = ("TMIN", "TMAX")


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

        for st in self.metadata.stations_by_id.values():
            if not (min_lat <= st.lat <= max_lat and min_lon <= st.lon <= max_lon):
                continue

            dist = haversine_km(lat, lon, st.lat, st.lon)
            if dist > radius_km:
                continue

            inv = self.metadata.inventory_by_id.get(st.stationId, {})

            # Muss TMIN und TMAX haben und beide müssen den Zeitraum abdecken
            tmin = inv.get("TMIN")
            tmax = inv.get("TMAX")
            if tmin is None or tmax is None:
                continue
            if not _passes_year_filter(tmin.firstYear, tmin.lastYear, start_year, end_year):
                continue
            if not _passes_year_filter(tmax.firstYear, tmax.lastYear, start_year, end_year):
                continue

            # Gemeinsamer Zeitraum (Schnittmenge)
            first_year = max(tmin.firstYear, tmax.firstYear)
            last_year = min(tmin.lastYear, tmax.lastYear)

            # Safety: falls irgendwann doch mal keine Überschneidung existiert
            if first_year > last_year:
                continue

            candidates.append(
                StationCandidate(
                    stationId=st.stationId,
                    name=st.name,
                    lat=st.lat,
                    lon=st.lon,
                    distanceKm=round(dist, 3),
                    availability=Availability(firstYear=first_year, lastYear=last_year),
                )
            )

        candidates.sort(key=attrgetter("distanceKm"))
        return candidates[:limit]