from datetime import datetime, timezone


class RetweetLimitHandler:
    def __init__(self):
        self.populated = False
        self.remaining = 0
        self.reset_time = datetime.now(timezone.utc)
        self.limit = 0

    def is_limit_exceeded(self) -> bool:
        return self.remaining == 0 and datetime.now(timezone.utc) < self.reset_time

    def update_limits(self, headers):
        self.populated = True
        remaining = int(headers.get("x-rate-limit-remaining", 0))
        reset = int(headers.get("x-rate-limit-reset", 0))
        limit = int(headers.get("x-rate-limit-limit", 0))

        if remaining:
            self.remaining = remaining
        if reset:
            self.reset_time = datetime.fromtimestamp(reset, timezone.utc)
        if limit:
            self.limit = limit

    @property
    def seconds_until_reset(self) -> int:
        """Returns the number of seconds until the rate limit resets."""
        reset_time = self.reset_time.replace(microsecond=0)
        time_to_wait = reset_time - datetime.now(timezone.utc)
        return int(time_to_wait.total_seconds())
