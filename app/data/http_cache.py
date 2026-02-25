from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path

import httpx


class HttpCache:
    def __init__(self, *, timeout_sec: int = 60, user_agent: str = "ghcn-temperature-api"):
        self.timeout_sec = timeout_sec
        self.user_agent = user_agent

    def get_to_file(self, url: str, dest: Path, *, max_age_seconds: int | None = None) -> bool:
        """
        Lädt eine URL in eine Datei (dateibasiertes Caching + atomarer Dateitausch).

        - Wenn dest existiert und max_age_seconds gesetzt ist:
            -> TTL prüfen (Datei ist "frisch" = Cache Hit) => kein Download
        - Wenn dest nicht existiert oder TTL abgelaufen ist:
            -> Download => dest wird atomar ersetzt

        Rückgabe:
          - True  = Download wurde gemacht (Cache Miss oder abgelaufen)
          - False = Cache Hit (Datei war vorhanden und noch "frisch")
        """

        # Zielordner sicherstellen (z.B. /cache/meta oder /cache/stations/by_station)
        dest.parent.mkdir(parents=True, exist_ok=True)

        # 1) Cache-Prüfung: existiert die Datei und ist sie innerhalb der TTL?
        #    Wenn ja => sofort raus (kein Netzwerk, keine Arbeit)
        if self._is_cache_hit(dest, max_age_seconds):
            return False

        # 2) Wir laden neu. Wichtig: Wir schreiben NIE direkt nach "dest",
        #    sondern immer erst in eine Temp-Datei und ersetzen dann atomar.
        #
        #    Warum? Damit niemals eine "halb geschriebene" Datei existiert,
        #    falls der Download unterbrochen wird oder parallel jemand liest.
        temp_dir, temp_file = self._create_temp_file(dest)

        try:
            # 3) Download in Temp-Datei (kann fehlschlagen; dest bleibt dabei unangetastet)
            self._download(url, temp_file)

            # 4) Atomarer Austausch:
            #    Entweder existiert die alte dest-Datei ODER schon die neue.
            #    Es gibt keinen Zwischenzustand "halb neu".
            self._replace_atomic(temp_file, dest)

            return True
        finally:
            # 5) Aufräumen: Temp-Ordner löschen (egal ob Erfolg oder Fehler)
            self._cleanup_temp_dir(temp_dir)

    def _is_cache_hit(self, dest: Path, max_age_seconds: int | None) -> bool:
        """
        Prüft, ob wir die Datei aus dem Cache verwenden können.

        Regeln:
        - Wenn max_age_seconds None ist => kein TTL-Cache aktiv => immer neu laden (False)
        - Wenn Datei nicht existiert => Cache Miss (False)
        - Sonst: Alter der Datei berechnen und mit TTL vergleichen
        """
        # Wenn keine TTL angegeben ist, soll immer neu geladen werden.
        if max_age_seconds is None:
            return False

        # Datei nicht vorhanden => Cache Miss
        if not dest.exists():
            return False

        # Alter in Sekunden (jetzt - letzte Änderungszeit)
        age_seconds = time.time() - dest.stat().st_mtime

        # Cache Hit, wenn Datei jünger/gleich TTL ist
        return age_seconds <= max_age_seconds

    def _download(self, url: str, out_file: Path) -> None:
        """
        Streamt die URL in eine Datei (out_file).

        - stream() => Download in kleinen Chunks (gut für große Dateien)
        - raise_for_status() => bei 404/500 usw. Exception, damit wir nicht "kaputtes" cachen
        """
        with httpx.Client(
            timeout=self.timeout_sec,
            headers={"User-Agent": self.user_agent},
            follow_redirects=True,
        ) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()

                # Binär schreiben
                with out_file.open("wb") as file_handle:
                    for chunk in response.iter_bytes():
                        if chunk:
                            file_handle.write(chunk)

    @staticmethod
    def _create_temp_file(dest: Path) -> tuple[Path, Path]:
        temp_dir = Path(tempfile.mkdtemp(prefix="dl_", dir=str(dest.parent)))
        temp_file = temp_dir / (dest.name + ".tmp")
        return temp_dir, temp_file

    @staticmethod
    def _replace_atomic(temp_file: Path, dest: Path) -> None:
        os.replace(temp_file, dest)

    @staticmethod
    def _cleanup_temp_dir(temp_dir: Path) -> None:
        shutil.rmtree(temp_dir, ignore_errors=True)