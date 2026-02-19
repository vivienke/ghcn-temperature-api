from __future__ import annotations

from pathlib import Path
import httpx


def download_stream(url: str, dest: Path, timeout_s: int = 60) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, timeout=timeout_s) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
