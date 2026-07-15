"""Small in-memory request limiter for the local public demo gateway."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from time import monotonic


@dataclass
class SlidingWindowRateLimiter:
    max_requests: int = 12
    window_seconds: float = 60.0
    _requests: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))

    def allow(self, key: str, now: float | None = None) -> tuple[bool, int]:
        current = monotonic() if now is None else now
        requests = self._requests[key]
        cutoff = current - self.window_seconds
        while requests and requests[0] <= cutoff:
            requests.popleft()
        if len(requests) >= self.max_requests:
            retry_after = max(1, int(requests[0] + self.window_seconds - current) + 1)
            return False, retry_after
        requests.append(current)
        return True, 0
