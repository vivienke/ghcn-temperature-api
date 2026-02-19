from __future__ import annotations
import math

EARTH_RADIUS_KM = 6371.0088  # mittlerer Erdradius

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c

def bounding_box(lat: float, lon: float, radius_km: float) -> tuple[float, float, float, float]:
    # grobe Vorfilterung: (minLat, maxLat, minLon, maxLon)
    lat_rad = math.radians(lat)
    delta_lat = radius_km / 111.32  # km pro Grad Breite

    # km pro Grad Länge hängt von cos(lat) ab
    cos_lat = max(1e-12, math.cos(lat_rad))
    delta_lon = radius_km / (111.32 * cos_lat)

    return (lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon)
