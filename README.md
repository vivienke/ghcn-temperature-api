# GHCN Temperature API

REST-API mit FastAPI für Stationssuche und Temperatur-Zeitreihen auf Basis von NOAA/GHCN-Daten.

## Features

- Health-Check
- Metadaten für UI-Grenzen
- Suche nach nahegelegenen Stationen
- Temperatur-Zeitreihe pro Station
- Caching für externe Datenabfragen

## Schnellstart (Docker, lokal für Entwicklung)

```bash
docker compose up --build
```

Danach erreichbar unter:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Konfiguration

Die Umgebungsvariablen werden in der `docker-compose.yml` gesetzt:

- `CACHE_DIR`: Verzeichnis für lokale Cache-Dateien.
- `METADATA_TTL_SEC`: Gültigkeitsdaür der Metadaten im Cache (Sekunden).
- `STATION_TTL_SEC`: Gültigkeitsdaür von Stationsdaten im Cache (Sekunden).
- `STATION_CACHE_LIMIT`: Maximale Anzahl gleichzeitig gecachter Stationsdateien.
- `HTTP_TIMEOUT_SEC`: Timeout für externe HTTP-Anfragen (Sekunden).

## Endpunkte

Basis-Pfad: `/api`

- `GET /api/health`: Einfache Verfügbarkeitsprüfung der API.
- `GET /api/meta`: Liefert UI-Grenzen wie Jahr-, Radius- und Limitbereiche.
- `GET /api/stations/nearby`: Sucht Stationen in der Nähe für einen Zeitraum.
- `GET /api/stations/{stationId}/series`: Liefert die Temperatur-Zeitreihe einer Station für einen Zeitraum.

## CORS

Erlaubte Origins:

- `http://localhost:8080`
- `http://127.0.0.1:8080`