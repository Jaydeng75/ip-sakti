import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    """Single-instance safety limit; use a gateway/Redis limiter for multi-instance production."""

    def __init__(self, app, requests: int, window_seconds: int):
        super().__init__(app)
        self.requests = requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/health/"):
            return await call_next(request)
        # The application trusts only the socket peer. A production gateway should
        # enforce the distributed limit before forwarding requests.
        client = request.client.host if request.client else "unknown"
        key = f"{client}:{request.url.path}"
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - self.window_seconds:
                hits.popleft()
            if len(hits) >= self.requests:
                retry_after = max(1, int(self.window_seconds - (now - hits[0])))
                return JSONResponse(
                    {"detail": "Rate limit exceeded. Retry later."},
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)
        return await call_next(request)
