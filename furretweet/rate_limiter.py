import time


class RateLimiter:
    def __init__(self, limit: int, period: int):
        self.limit = limit
        self.period = period
        self.tokens = 0

    def consume(self):
        self.update_tokens()
        if self.tokens < 1:
            return False
        self.tokens -= 1
        return True

    def update_tokens(self):
        now = time.monotonic()
        time_since_update = now - self.last_update
        new_tokens = time_since_update * self.limit / self.period
        self.tokens = min(self.limit, self.tokens + new_tokens)
        self.last_update = now
