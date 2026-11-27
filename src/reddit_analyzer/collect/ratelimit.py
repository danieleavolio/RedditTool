"""Client-side pacing driven by Reddit's ``X-Ratelimit-*`` headers.

This only ever slows the client down. It never tries to get around Reddit's limits.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

import httpx


def _num(value: str | None) -> float | None:
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


@dataclass
class RateLimiter:
    reserve: int = 5  # wait for the window to reset when remaining quota drops below this
    sleep: Callable[[float], None] = time.sleep
    rng: Callable[[], float] = random.random
    used: float | None = field(default=None, init=False)
    remaining: float | None = field(default=None, init=False)
    reset: float | None = field(default=None, init=False)  # seconds until the window resets

    def update(self, headers: Mapping[str, str]) -> None:
        h = httpx.Headers(headers)
        used, remaining, reset = (
            _num(h.get("x-ratelimit-used")),
            _num(h.get("x-ratelimit-remaining")),
            _num(h.get("x-ratelimit-reset")),
        )
        # Keep the last known value when a response (e.g. a 5xx) lacks the headers.
        self.used = used if used is not None else self.used
        self.remaining = remaining if remaining is not None else self.remaining
        self.reset = reset if reset is not None else self.reset

    def before_request(self) -> float:
        """Sleep until the quota window resets if the remaining quota is nearly gone."""
        if self.remaining is None or self.remaining >= self.reserve:
            return 0.0
        wait = (self.reset or 1.0) + 1.0
        self.sleep(wait)
        self.remaining = None  # unknown until the next response
        return wait

    def wait_backoff(self, attempt: int, retry_after: float | None = None) -> float:
        """Sleep with exponential backoff and jitter; never less than ``retry_after``."""
        base = min(60.0, 2.0**attempt)
        delay = base / 2 + self.rng() * base / 2
        if retry_after is not None:
            delay = max(delay, retry_after)
        self.sleep(delay)
        return delay
