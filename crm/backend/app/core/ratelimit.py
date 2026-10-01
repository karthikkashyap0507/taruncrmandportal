"""In-memory sliding-window rate limiting (the API runs as a single process)."""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, detail: str = "Too many requests. Please slow down and try again shortly.") -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.max_calls:
                retry_after = int(self.window - (now - q[0])) + 1
                raise HTTPException(status_code=429, detail=detail, headers={"Retry-After": str(retry_after)})
            q.append(now)
            if len(self._hits) > 10000:  # drop idle keys so memory stays bounded
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] > self.window]:
                    del self._hits[k]


def client_ip(request: Request) -> str:
    # uvicorn trusts nginx's X-Forwarded-For (proxy_headers), so this is the real visitor IP
    return request.client.host if request.client else "unknown"


login_ip_limiter = RateLimiter(20, 60)
register_ip_limiter = RateLimiter(10, 3600)
forgot_ip_limiter = RateLimiter(5, 900)
forgot_email_limiter = RateLimiter(3, 3600)
upload_user_limiter = RateLimiter(20, 600)
