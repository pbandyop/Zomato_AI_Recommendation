from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException


class RateLimiter:
    """Simple in-memory per-IP fixed window (approximate 60s) limiter."""

    __slots__ = ("_max_per_minute", "_by_ip", "_lock")

    def __init__(self, max_per_minute: int) -> None:
        self._max_per_minute = max_per_minute
        self._by_ip: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, client_ip: str) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._by_ip[client_ip]
            while q and now - q[0] > 60.0:
                q.popleft()
            if len(q) >= self._max_per_minute:
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests; try again in a minute.",
                )
            q.append(now)
