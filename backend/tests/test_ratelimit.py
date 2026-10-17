import pytest

from app.ratelimit import RateLimiter, RateLimitExceeded


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_allows_calls_up_to_the_limit():
    limiter = RateLimiter(3, window_s=60, clock=Clock())
    assert [limiter.reserve() for _ in range(3)] == [0.0, 0.0, 0.0]


def test_rejects_when_the_wait_is_too_long():
    clock = Clock()
    limiter = RateLimiter(2, window_s=60, clock=clock)
    limiter.reserve(2)
    clock.now = 10.0
    with pytest.raises(RateLimitExceeded) as info:
        limiter.reserve(1, max_wait=5.0)
    assert info.value.retry_after == pytest.approx(50.0)


def test_waits_when_allowed_and_books_the_slot():
    limiter = RateLimiter(2, window_s=60, clock=Clock())
    limiter.reserve(2)
    assert limiter.reserve(1, max_wait=100.0) == pytest.approx(60.0)
    with pytest.raises(RateLimitExceeded):
        limiter.reserve(1, max_wait=0.0)


def test_old_calls_expire():
    clock = Clock()
    limiter = RateLimiter(1, window_s=60, clock=clock)
    limiter.reserve()
    clock.now = 61.0
    assert limiter.reserve() == 0.0


def test_too_many_calls_in_one_request_is_a_bug():
    with pytest.raises(ValueError):
        RateLimiter(2).reserve(3)
