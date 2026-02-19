from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional, Tuple

from app.services.data_service import download_stream

AWS_BASE = "https://noaa-ghcn-pds.s3.amazonaws.com"
STATIONS_URL = f"{AWS_BASE}/ghcnd-stations.txt"
INVENTORY_URL = f"{AWS_BASE}/ghcnd-inventory.txt"


@dataclass(frozen=True)
class MetadataPaths:
    stations: Path
    inventory: Path
    refreshedOn: str  # ISO date, z.B. "2026-02-19"


# In-Memory Cache (damit minYear nicht ständig neu gescannt wird)
_cached_min_year: Optional[int] = None
_cached_min_year_on: Optional[str] = None


def ensure_metadata(cache_dir: str) -> MetadataPaths:
    """
    Lädt ghcnd-stations.txt und ghcnd-inventory.txt maximal 1x pro Tag.
    Alte Version wird überschrieben (kein Wachstum).
    """
    meta_dir = Path(cache_dir) / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)

    stations_path = meta_dir / "ghcnd-stations.txt"
    inventory_path = meta_dir / "ghcnd-inventory.txt"
    state_path = meta_dir / "state.json"

    today = date.today().isoformat()
    last_refresh = _read_last_refresh(state_path)

    if last_refresh != today:
        download_stream(STATIONS_URL, stations_path)
        download_stream(INVENTORY_URL, inventory_path)
        _write_last_refresh(state_path, today)

        # minYear Cache ungültig, weil neue inventory geladen
        _invalidate_min_year_cache()

    # Safety: falls Dateien fehlen, erzwingen
    if not stations_path.exists() or not inventory_path.exists():
        download_stream(STATIONS_URL, stations_path)
        download_stream(INVENTORY_URL, inventory_path)
        _write_last_refresh(state_path, today)
        _invalidate_min_year_cache()

    refreshed_on = _read_last_refresh(state_path) or today
    return MetadataPaths(stations=stations_path, inventory=inventory_path, refreshedOn=refreshed_on)


def get_ui_max_year() -> int:
    """
    Maximal erlaubtes Endjahr ist das Vorjahr.
    """
    return date.today().year - 1


def get_ui_min_year(cache_dir: str) -> int:
    """
    Minimales Startjahr für die UI wird aus ghcnd-inventory.txt ermittelt.
    Da im Projekt TMIN und TMAX required sind, betrachten wir beide Elemente.

    Strategie (einfach, robust):
    - Scanne inventory und finde:
      - global kleinstes FIRSTYEAR für TMIN
      - global kleinstes FIRSTYEAR für TMAX
    - UI-minYear = max(minTMIN, minTMAX)
      -> damit ist garantiert, dass es ab UI-minYear prinzipiell Stationen mit TMIN+TMAX geben kann.
    """
    global _cached_min_year, _cached_min_year_on

    paths = ensure_metadata(cache_dir)
    if _cached_min_year is not None and _cached_min_year_on == paths.refreshedOn:
        return _cached_min_year

    min_tmin, min_tmax = _scan_inventory_min_years(paths.inventory)

    # Falls eine Kategorie gar nicht gefunden wird (sollte praktisch nicht passieren)
    if min_tmin is None and min_tmax is None:
        result = 0
    elif min_tmin is None:
        result = min_tmax
    elif min_tmax is None:
        result = min_tmin
    else:
        result = max(min_tmin, min_tmax)

    _cached_min_year = int(result)
    _cached_min_year_on = paths.refreshedOn
    return _cached_min_year


def _scan_inventory_min_years(inventory_path: Path) -> Tuple[Optional[int], Optional[int]]:
    """
    Inventory fixed-width:
      ID(11) LAT(9) LON(10) ELEMENT(4) FIRSTYEAR(4) LASTYEAR(4)
    ELEMENT beginnt bei Index 31..35
    FIRSTYEAR 36..40
    """
    min_tmin: Optional[int] = None
    min_tmax: Optional[int] = None

    with inventory_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(line) < 45:
                continue

            element = line[31:35].strip()
            if element not in ("TMIN", "TMAX"):
                continue

            try:
                first_year = int(line[36:40].strip())
            except ValueError:
                continue

            if element == "TMIN":
                if min_tmin is None or first_year < min_tmin:
                    min_tmin = first_year
            else:
                if min_tmax is None or first_year < min_tmax:
                    min_tmax = first_year

    return min_tmin, min_tmax


def _read_last_refresh(state_path: Path) -> Optional[str]:
    if not state_path.exists():
        return None
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        value = data.get("last_meta_refresh")
        if isinstance(value, str) and value:
            return value
        return None
    except Exception:
        return None


def _write_last_refresh(state_path: Path, today: str) -> None:
    state_path.write_text(
        json.dumps({"last_meta_refresh": today}, indent=2),
        encoding="utf-8",
    )


def _invalidate_min_year_cache() -> None:
    global _cached_min_year, _cached_min_year_on
    _cached_min_year = None
    _cached_min_year_on = None
