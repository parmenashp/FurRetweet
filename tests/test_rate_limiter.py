import pytest
from datetime import datetime, timezone, timedelta
from furretweet.rate_limiter import RetweetLimitHandler
from freezegun import freeze_time


def test_is_limit_exceeded():
    handler = RetweetLimitHandler()

    handler.remaining = 1
    handler.reset_time = datetime.now(timezone.utc) + timedelta(seconds=10)
    assert not handler.is_limit_exceeded()

    handler.remaining = 0
    handler.reset_time = datetime.now(timezone.utc) + timedelta(seconds=10)
    assert handler.is_limit_exceeded()

    handler.remaining = 0
    handler.reset_time = datetime.now(timezone.utc) - timedelta(seconds=10)
    assert not handler.is_limit_exceeded()


def test_update_limits():
    handler = RetweetLimitHandler()
    headers = {
        "x-rate-limit-remaining": "10",
        "x-rate-limit-reset": str(int(datetime.now(timezone.utc).timestamp()) + 10),
        "x-rate-limit-limit": "15",
    }

    assert not handler.populated

    handler.update_limits(headers)

    assert handler.populated
    assert handler.remaining == 10
    assert handler.reset_time.timestamp() == int(headers["x-rate-limit-reset"])
    assert handler.limit == 15


def test_seconds_until_reset():
    initial_datetime = datetime(year=1, month=7, day=12, hour=15, minute=6, second=3)

    with freeze_time(initial_datetime) as frozen_datetime:
        handler = RetweetLimitHandler()
        now = datetime.now(timezone.utc)
        reset_time = now + timedelta(seconds=20)
        handler.reset_time = reset_time
        assert handler.seconds_until_reset == 20

        frozen_datetime.tick(delta=timedelta(seconds=5))
        assert handler.seconds_until_reset == 15
