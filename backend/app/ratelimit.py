"""Sliding-window limiter that keeps us under the free-tier requests-per-minute limit."""
import threading
import time
from collections import deque
from collections.abc import Callable


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: float) -> None:
        super().__init__(f"Rate limit reached, retry in {retry_after:.1f} s")
        self.retry_after = retry_after


class RateLimiter:
    def __init__(
        self,
        max_calls: int,
        window_s: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_calls < 1:
            raise ValueError("max_calls must be at least 1")
        self.max_calls = max_calls
        self.window_s = window_s
        self._clock = clock
        self._events: deque[float] = deque()  # times at which calls are (or will be) made
        self._lock = threading.Lock()

    def reserve(self, n: int = 1, max_wait: float = 0.0) -> float:
        """Book n calls. Returns how many seconds to wait first (0.0 = go now).

        Raises RateLimitExceeded if the wait would be longer than max_wait (nothing is booked).
        """
        if n < 1 or n > self.max_calls:
            raise ValueError("n must be between 1 and max_calls")
        with self._lock:
            now = self._clock()
            while self._events and self._events[0] <= now - self.window_s:
                self._events.popleft()

            when = now
            overflow = len(self._events) + n - self.max_calls
            if overflow > 0:
                when = max(when, self._events[overflow - 1] + self.window_s)
            if self._events and self._events[-1] > when:
                when = self._events[-1]  # keep bookings in order

            wait = when - now
            if wait > max_wait:
                raise RateLimitExceeded(wait)
            self._events.extend([when] * n)
            return wait
