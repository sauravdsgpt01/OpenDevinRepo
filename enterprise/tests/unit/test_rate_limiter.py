"""Unit tests for the RateLimiter class."""

import threading
import time

from sync.resend_keycloak import RateLimiter


class TestRateLimiter:
    """Test cases for RateLimiter."""

    def test_first_call_no_wait(self):
        """First call should not wait."""
        limiter = RateLimiter(requests_per_second=2.0, safety_margin=0.0)
        start = time.monotonic()
        limiter.wait()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1

    def test_respects_rate_limit(self):
        """Consecutive calls should respect the rate limit."""
        limiter = RateLimiter(requests_per_second=10.0, safety_margin=0.0)
        start = time.monotonic()
        for _ in range(3):
            limiter.wait()
        elapsed = time.monotonic() - start
        # 3 calls at 10 req/s should take at least 0.2s (2 intervals of 0.1s)
        assert elapsed >= 0.18

    def test_safety_margin_reduces_rate(self):
        """Safety margin should reduce the effective rate."""
        # 2 req/s with 50% safety margin = 1 req/s effective
        limiter = RateLimiter(requests_per_second=2.0, safety_margin=0.5)
        start = time.monotonic()
        for _ in range(2):
            limiter.wait()
        elapsed = time.monotonic() - start
        # 2 calls at 1 req/s effective should take at least 1.0s
        assert elapsed >= 0.95

    def test_thread_safety(self):
        """RateLimiter should be thread-safe."""
        limiter = RateLimiter(requests_per_second=10.0, safety_margin=0.0)
        call_count = 0
        lock = threading.Lock()

        def make_calls():
            nonlocal call_count
            for _ in range(5):
                limiter.wait()
                with lock:
                    call_count += 1

        threads = [threading.Thread(target=make_calls) for _ in range(3)]
        start = time.monotonic()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.monotonic() - start

        # 15 total calls at 10 req/s should take at least 1.4s (14 intervals)
        assert call_count == 15
        assert elapsed >= 1.3

    def test_default_safety_margin(self):
        """Default safety margin should be 10%."""
        # 2 req/s with 10% safety margin = 1.8 req/s effective = ~0.556s interval
        limiter = RateLimiter(requests_per_second=2.0)
        start = time.monotonic()
        for _ in range(3):
            limiter.wait()
        elapsed = time.monotonic() - start
        # 3 calls with ~0.556s interval should take at least 1.1s (2 intervals)
        assert elapsed >= 1.0
