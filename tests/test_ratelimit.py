from reddit_analyzer.collect.ratelimit import RateLimiter


def _limiter(**kw):
    sleeps = []
    return RateLimiter(sleep=sleeps.append, rng=lambda: 0.5, **kw), sleeps


def test_update_parses_headers():
    limiter, _ = _limiter()
    limiter.update(
        {"X-Ratelimit-Used": "12", "X-Ratelimit-Remaining": "88.0", "X-Ratelimit-Reset": "41"}
    )
    assert (limiter.used, limiter.remaining, limiter.reset) == (12, 88, 41)


def test_update_keeps_last_values_when_headers_missing_or_garbage():
    limiter, _ = _limiter()
    limiter.update({"x-ratelimit-remaining": "50", "x-ratelimit-reset": "10"})
    limiter.update({"x-ratelimit-remaining": "nope"})
    assert limiter.remaining == 50 and limiter.reset == 10


def test_no_wait_when_quota_is_plentiful_or_unknown():
    limiter, sleeps = _limiter(reserve=5)
    assert limiter.before_request() == 0
    limiter.update({"x-ratelimit-remaining": "5", "x-ratelimit-reset": "30"})
    assert limiter.before_request() == 0
    assert sleeps == []


def test_waits_for_reset_when_quota_nearly_gone():
    limiter, sleeps = _limiter(reserve=5)
    limiter.update({"x-ratelimit-remaining": "4", "x-ratelimit-reset": "30"})
    assert limiter.before_request() == 31
    assert sleeps == [31]
    assert limiter.before_request() == 0  # quota unknown again until the next response


def test_backoff_grows_exponentially_with_jitter_and_is_capped():
    limiter, sleeps = _limiter()
    delays = [limiter.wait_backoff(a) for a in range(0, 10)]
    assert delays[:4] == [0.75, 1.5, 3.0, 6.0]  # base/2 + 0.5 * base/2
    assert max(delays) == 45.0  # capped at 60s base
    assert sleeps == delays


def test_backoff_honours_retry_after():
    limiter, _ = _limiter()
    assert limiter.wait_backoff(0, retry_after=30) == 30
    assert limiter.wait_backoff(5, retry_after=1) == 24.0
