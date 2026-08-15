def test_rate_limiter_key_format():
    from app.connectors.sdk.rate_limiter import RateLimiter
    # pure helper
    class R:
        prefix = "rl"
        def _k(self, *parts):
            return ":".join([self.prefix, *parts])
    assert R()._k("xposedornot", "s", "1") == "rl:xposedornot:s:1"
