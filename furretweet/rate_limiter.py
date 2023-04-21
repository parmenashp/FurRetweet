from datetime import datetime, timedelta, timezone
import time

from loguru import logger


class RetweetLimitHandler:
    def __init__(self) -> None:
        self.populated = False
        self.remaining = -1
        self.reset_time = datetime.now(timezone.utc)
        self.limit = 0

    def is_limit_exceeded(self) -> bool:
        """Returns whether the rate limit has been exceeded."""
        return (
            self.populated and self.remaining == 0 and self.reset_time > datetime.now(timezone.utc)
        )

    def update_limits(self, headers) -> None:
        self.populated = True
        remaining = int(headers.get("x-rate-limit-remaining", 0))
        reset_timestamp = int(headers.get("x-rate-limit-reset", 0))
        limit = int(headers.get("x-rate-limit-limit", 0))

        if remaining:
            self.remaining = remaining
        if reset_timestamp:
            self.reset_time = datetime.fromtimestamp(reset_timestamp, timezone.utc)
        if limit:
            self.limit = limit

    @property
    def seconds_until_reset(self) -> int:
        """Returns the number of seconds until the rate limit resets."""
        reset_time = self.reset_time.replace(microsecond=0)
        time_to_wait = reset_time - datetime.now(timezone.utc)
        return int(time_to_wait.total_seconds())
