from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """Enforces a maximum throughput across all tool calls."""

    def __init__(self, max_per_second: float = 1.0, daily_max: int = 500):
        self._min_interval = 1.0 / max_per_second
        self._last_call: float = 0.0
        self._lock = asyncio.Lock()
        self._daily_max = daily_max
        self._day_calls = 0
        self._day_reset = 0.0

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            if now - self._day_reset > 86400:
                self._day_calls = 0
                self._day_reset = now
            if self._day_calls >= self._daily_max:
                wait = 86400 - (now - self._day_reset)
                raise RuntimeError(
                    f"Daily limit of {self._daily_max} requests reached. "
                    f"Resets in {int(wait // 3600)}h{int((wait % 3600) // 60)}m."
                )
            self._day_calls += 1

            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()
