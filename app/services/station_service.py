from __future__ import annotations

from typing import List

from app.schemas import StationResult, StationAvailability
from app.services.geo import bounding_box, haversine_km
from app.services.metadata_store import metadata_store

REQUIRED_ELEMENTS = ("TMIN", "TMAX")


def _passes_year_filter(first: int, last: int, start_year: int, end_year: int) -> bool:
    # Station muss den gewünschten Zeitraum abdecken (Lücken innerhalb sind erlaubt)
    return first <= start_year and last >= end_year


def find_nearby_stations(
    lat: float,
    lon: float,
    radius_km: int,
    limit: int,
    start_year: int,
    end_year: int,
    cache_dir: str = "/cache",
) -> List[StationResult]:
    # Metadaten lazy laden (Stations + Inventory)
    metadata_store.ensure_loaded(cache_dir)

    min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius_km)

    results: List[StationResult] = []

    for st in metadata_store.stations_by_id.values():
        # Bounding-box Vorfilter (schnell)
        if not (min_lat <= st.lat <= max_lat and min_lon <= st.lon <= max_lon):
            continue

        # genaue Distanz (Erdkrümmung via Haversine)
        dist = haversine_km(lat, lon, st.lat, st.lon)
        if dist > radius_km:
            continue

        inv = metadata_store.inventory_by_id.get(st.stationId, {})

        # Projektregel: TMIN und TMAX müssen beide im Zeitraum vorhanden sein
        ok = all(
            e in inv and _passes_year_filter(inv[e].firstYear, inv[e].lastYear, start_year, end_year)
            for e in REQUIRED_ELEMENTS
        )
        if not ok:
            continue

        availability = {
            k: StationAvailability(firstYear=v.firstYear, lastYear=v.lastYear)
            for k, v in inv.items()
        }

        results.append(
            StationResult(
                stationId=st.stationId,
                name=st.name,
                lat=st.lat,
                lon=st.lon,
                distanceKm=round(dist, 3),
                availability=availability,
            )
        )

    results.sort(key=lambda x: x.distanceKm)
    return results[:limit]
