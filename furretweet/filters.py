from typing import TypeVar
from furretweet.models import Tweet, StreamResponse

from datetime import datetime, timezone, timedelta


class BaseFilter:
    def filter(self, response: StreamResponse) -> bool:
        """Should return False if the tweet should be
        filtered out and True if it should be kept."""
        raise NotImplementedError

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


Filter = TypeVar("Filter", bound=BaseFilter)


# class FancamFilter(BaseFilter):
#     def filter(self, response: StreamResponse) -> bool:
#         pass


class MinimumFollowersFilter(BaseFilter):
    def __init__(self, minimum: int):
        self.minimum = minimum

    def filter(self, response: StreamResponse) -> bool:
        if response.author.public_metrics.followers_count < self.minimum:
            return False
        return True


class NsfwFilter(BaseFilter):
    def filter(self, response: StreamResponse) -> bool:
        return not response.tweet.possibly_sensitive


class AccountAgeFilter(BaseFilter):
    def __init__(self, minimum: int):
        self.minimum = minimum

    def filter(self, response: StreamResponse) -> bool:
        if response.author.created_at < datetime.now(timezone.utc) - timedelta(days=self.minimum):
            return True
        return False


class MaxNewLinesFilter(BaseFilter):
    def __init__(self, maximum: int):
        self.maximum = maximum

    def filter(self, response: StreamResponse) -> bool:
        if response.tweet.text.count("\n") > self.maximum:
            return False
        return True


class FursuitFridayOnlyFilter(BaseFilter):
    def filter(self, response: StreamResponse) -> bool:
        if response.tweet.text.lower().strip() == "#fursuitfriday":
            return False
        return True


class MediaFilter(BaseFilter):
    def filter(self, response: StreamResponse) -> bool:
        if response.includes.media:
            return True
        return False


# class VerifiedFilter(BaseFilter):
#     pass


class NumberHashtagsFilter(BaseFilter):
    def __init__(self, minimum: int):
        self.minimum = minimum

    def filter(self, response: StreamResponse) -> bool:
        # If entities is None or [] or get("hashtags") is None, return True
        if not response.tweet.entities or not response.tweet.entities.get("hashtags"):
            return True
        if len(response.tweet.entities["hashtags"]) > self.minimum:
            return False
        return True


class BannedTermsFilter(BaseFilter):
    def filter(self, response: StreamResponse) -> bool:
        if any(term in response.tweet.text.lower() for term in self.banned_words):
            return False
        return True

    banned_words = [
        "zoofilia",
        "zoophila",
        "nsfw",
        "trump",
        "trending",
        "kpop",
        "animalporn",
        "furryporn",
        "furrysex",
        "animalsex",
        "animaldicks",
        "hitler",
        "furrydicks",
        "gayanimal",
        "fridayvibes",
        "blackoutbts",
        "yiff",
        "bdsm",
        "catsoftwitter",
        "fancam",
        "bolsonaro",
        "murrsuit",
        "bts",
        "porn",
        "obama",
        "biden",
        "beat a furry",
        "fridaythoughts",
        "fundy",
        "🔞",
        "🍆",
        "🍑",
        "blood",
        "commission",
        "wip",
        "my fursuit",
        "anus",
        "fucking furries",
        "stupid",
        "fart",
        "pyro",
        "floppa",
        "monk",
        "kill furry",
        "crypto",
        "nft",
        "fuck me",
        "fuck you",
        "murr",
        "bitcoin",
        "giveaway",
        "limited time",
        "earn money",
        "investment",
        "lula",
        "no minors",
    ]
