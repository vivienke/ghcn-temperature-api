from typing import List, Optional
from app.schemas import StationResult

def find_nearby_stations(
    lat: float,
    lon: float,
    radius_km: int,
    limit: int,
    start_year: int,
    end_year: int,
    require_elements: Optional[list[str]] = None,
    mode: str = "strict",
) -> List[StationResult]:
    # TODO: später Metadaten laden + bounding box + Distanz + Inventory-Filter
    # Stub: liefert erstmal leer zurück
    return []