#!/usr/bin/env python3
"""Tests for the RateLimiter class in resend_keycloak.py."""

import threading
import time
import unittest

from enterprise.sync.resend_keycloak import RateLimiter


class TestRateLimiter(unittest.TestCase):
    """Tests for the RateLimiter class."""

    def test_first_call_no_wait(self):
        """First call should not wait."""
        limiter = RateLimiter(requests_per_second=2.0, safety_margin=0.0)
        start = time.monotonic()
        limiter.wait()
        elapsed = time.monotonic() - start
        # First call should be immediate (< 10ms)
        self.assertLess(elapsed, 0.01)

    def test_rate_limiting(self):
        """Subsequent calls should wait to respect rate limit."""
        limiter = RateLimiter(requests_per_second=2.0, safety_margin=0.0)
        # Expected interval: 0.5s for 2 req/s

        limiter.wait()  # First call - no wait
        start = time.monotonic()
        limiter.wait()  # Second call - should wait ~0.5s
        elapsed = time.monotonic() - start

        # Should wait approximately 0.5s (allow 50ms tolerance)
        self.assertGreaterEqual(elapsed, 0.45)
        self.assertLess(elapsed, 0.55)

    def test_safety_margin(self):
        """Safety margin should increase wait time."""
        limiter = RateLimiter(requests_per_second=2.0, safety_margin=0.1)
        # Expected interval: 0.5s * 1.1 = 0.55s

        limiter.wait()  # First call - no wait
        start = time.monotonic()
        limiter.wait()  # Second call - should wait ~0.55s
        elapsed = time.monotonic() - start

        # Should wait approximately 0.55s (allow 50ms tolerance)
        self.assertGreaterEqual(elapsed, 0.5)
        self.assertLess(elapsed, 0.65)

    def test_thread_safety(self):
        """Rate limiter should be thread-safe."""
        limiter = RateLimiter(requests_per_second=2.0, safety_margin=0.0)
        call_times = []
        lock = threading.Lock()

        def make_call():
            limiter.wait()
            with lock:
                call_times.append(time.monotonic())

        # Create 4 threads that all try to make calls
        threads = [threading.Thread(target=make_call) for _ in range(4)]
        start = time.monotonic()

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total_time = time.monotonic() - start

        # 4 calls at 2 req/s should take at least 1.5s (3 intervals of 0.5s)
        # Allow some tolerance for thread scheduling
        self.assertGreaterEqual(total_time, 1.4)

        # Verify calls were properly spaced
        call_times.sort()
        for i in range(1, len(call_times)):
            interval = call_times[i] - call_times[i - 1]
            # Each interval should be at least ~0.5s (allow some tolerance)
            self.assertGreaterEqual(interval, 0.45)

    def test_no_wait_after_sufficient_time(self):
        """No wait needed if enough time has passed since last call."""
        limiter = RateLimiter(requests_per_second=2.0, safety_margin=0.0)

        limiter.wait()  # First call
        time.sleep(0.6)  # Wait longer than required interval

        start = time.monotonic()
        limiter.wait()  # Second call - should not need to wait
        elapsed = time.monotonic() - start

        # Should be immediate (< 10ms)
        self.assertLess(elapsed, 0.01)


if __name__ == '__main__':
    unittest.main()
