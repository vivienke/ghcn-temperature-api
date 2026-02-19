import os
from fastapi import FastAPI
from app.routes import router as api_router
from app.services.metadata_store import metadata_store

app = FastAPI(title="GHCN Temperature API")
app.include_router(api_router)

@app.on_event("startup")
def warmup():
    cache_dir = os.getenv("CACHE_DIR", "/cache")
    metadata_store.ensure_loaded(cache_dir)