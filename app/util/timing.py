import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

log = logging.getLogger(__name__)

class RequestTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        response.headers["X-Request-Time-ms"] = str(elapsed_ms)
        log.info("%s %s -> %s (%d ms)", request.method, request.url.path, response.status_code, elapsed_ms)
        return response
