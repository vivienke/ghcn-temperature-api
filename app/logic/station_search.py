from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional

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
    availability: Dict[str, Availability]

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

        #Bounding Box gibt Tuple (minLat, maxLat, minLon, maxLon) zurück
        min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius_km)
        candidates: List[StationCandidate] = []

        
        for st in self.metadata.stations_by_id.values():
            if not (min_lat <= st.lat <= max_lat and min_lon <= st.lon <= max_lon):
                continue

            dist = haversine_km(lat, lon, st.lat, st.lon)
            if dist > radius_km:
                continue

            inv = self.metadata.inventory_by_id.get(st.stationId, {})
            ok = True
            for e in REQUIRED_ELEMENTS:
                if e not in inv:
                    ok = False
                    break
                a = inv[e]
                if not _passes_year_filter(a.firstYear, a.lastYear, start_year, end_year):
                    ok = False
                    break
            if not ok:
                continue

            candidates.append(
                StationCandidate(
                    stationId=st.stationId,
                    name=st.name,
                    lat=st.lat,
                    lon=st.lon,
                    distanceKm=round(dist, 3),
                    availability=inv,  # raw Availability objects
                )
            )

        candidates.sort(key=lambda x: x.distanceKm)
        return candidates[:limit]
