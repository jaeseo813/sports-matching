"""고정 윈도우 레이트리밋 (인메모리). Redis 구현으로 교체할 자리."""

import time
from collections import defaultdict

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def reset(self) -> None:
        self._hits.clear()

    def __call__(self, request: Request) -> None:
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        recent = [t for t in self._hits[key] if now - t < self.window]
        if len(recent) >= self.limit:
            self._hits[key] = recent
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "RATE_LIMITED",
                    "message": "요청이 너무 많습니다. 잠시 후 다시 시도하세요",
                },
            )
        recent.append(now)
        self._hits[key] = recent


login_limiter = RateLimiter(limit=5, window_seconds=60)  # 로그인 5/분
