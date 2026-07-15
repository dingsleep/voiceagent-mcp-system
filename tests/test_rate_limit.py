import unittest

from voice_agent_mcp.rate_limit import SlidingWindowRateLimiter


class RateLimitTest(unittest.TestCase):
    def test_blocks_after_limit_with_retry_time(self):
        limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=10)

        self.assertEqual(limiter.allow("127.0.0.1", now=0), (True, 0))
        self.assertEqual(limiter.allow("127.0.0.1", now=1), (True, 0))
        self.assertEqual(limiter.allow("127.0.0.1", now=2), (False, 9))

    def test_window_expiry_allows_new_request(self):
        limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=10)

        limiter.allow("127.0.0.1", now=0)
        self.assertEqual(limiter.allow("127.0.0.1", now=10), (True, 0))
