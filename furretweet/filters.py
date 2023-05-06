import re
from typing import TypeVar
from furretweet.models import Tweet, StreamResponse
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta


Filter = TypeVar("Filter", bound="BaseFilter")


class BaseFilter(ABC):
    @abstractmethod
    def filter(self, response: StreamResponse) -> bool:
        """Should return False if the tweet should be
        filtered out and True if it should be kept."""
        raise NotImplementedError

    @property
    @abstractmethod
    def details(self) -> dict:
        """Should return a dict with details about the
        filter or an empty dict if not applicable."""
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"<{self.name}>"


class MinimumFollowersFilter(BaseFilter):
    def __init__(self, min_followers: int):
        self.min_followers = min_followers

    def filter(self, response: StreamResponse) -> bool:
        self.response = response
        if response.author.public_metrics.followers_count < self.min_followers:
            return False
        return True

    @property
    def details(self) -> dict:
        return {
            "min_followers": self.min_followers,
            "followers_count": self.response.author.public_metrics.followers_count,
        }


class NsfwFilter(BaseFilter):
    def filter(self, response: StreamResponse) -> bool:
        return not response.tweet.possibly_sensitive

    @property
    def details(self) -> dict:
        return {}


class MinimumAccountAgeFilter(BaseFilter):
    def __init__(self, min_days: int):
        self.min_days = min_days

    def filter(self, response: StreamResponse) -> bool:
        self.response = response
        self.now = datetime.now(tz=timezone.utc)
        if response.author.created_at < self.now - timedelta(days=self.min_days):
            return True
        return False

    @property
    def details(self) -> dict:
        return {
            "min_account_days": self.min_days,
            "account_created_at": self.response.author.created_at,
            "checked_at": self.now,
        }


class MaximumNewLinesFilter(BaseFilter):
    def __init__(self, max: int):
        self.max = max

    def filter(self, response: StreamResponse) -> bool:
        self.response = response
        self.count = response.tweet.text.count("\n")
        if self.count > self.max:
            return False
        return True

    @property
    def details(self) -> dict:
        return {
            "max_new_lines": self.max,
            "new_lines_count": self.count,
        }


class FursuitFridayOnlyFilter(BaseFilter):
    def remove_tco_links(self, text: str) -> str:
        pattern = r"https?://t\.co/\w+"
        return re.sub(pattern, "", text)

    def filter(self, response: StreamResponse) -> bool:
        text = self.remove_tco_links(response.tweet.text)
        if text.lower().strip() == "#fursuitfriday":
            return False
        return True

    @property
    def details(self) -> dict:
        return {}


class MediaFilter(BaseFilter):
    def filter(self, response: StreamResponse) -> bool:
        if response.includes.media:
            return True
        return False

    @property
    def details(self) -> dict:
        return {}


class MaximumHashtagsFilter(BaseFilter):
    def __init__(self, max: int):
        self.max = max

    def filter(self, response: StreamResponse) -> bool:
        if not response.tweet.entities or not response.tweet.entities.get("hashtags"):
            return True

        self.count = len(response.tweet.entities["hashtags"])

        if self.count > self.max:
            return False
        return True

    @property
    def details(self) -> dict:
        return {
            "max_hashtags": self.max,
            "hashtags_count": self.count,
        }


class BannedTermsFilter(BaseFilter):
    def filter(self, response: StreamResponse) -> bool:
        self.terms_found = [
            terms for terms in self.banned_terms if terms.lower() in response.tweet.text.lower()
        ]

        if self.terms_found:
            return False
        return True

    @property
    def details(self) -> dict:
        return {
            "terms_found": self.terms_found,
        }

    banned_terms = [
        "animaldicks",
        "animalporn",
        "animalsex",
        "anus",
        "bdsm",
        "beat a furry",
        "biden",
        "bitcoin",
        "blackoutbts",
        "blood",
        "bolsonaro",
        "bts",
        "bussy",
        "catsoftwitter",
        "commission",
        "crypto",
        "earn money",
        "fancam",
        "fart",
        "floppa",
        "fridaythoughts",
        "fridayvibes",
        "fuck me",
        "fuck you",
        "fucking furries",
        "fundy",
        "furrydicks",
        "furryporn",
        "furrysex",
        "gayanimal",
        "giveaway",
        "hitler",
        "investment",
        "kill furry",
        "kpop",
        "limited time",
        "lula",
        "monk",
        "murr",
        "murrsuit",
        "my fursuit",
        "nft",
        "no minors",
        "nsfw",
        "obama",
        "porn",
        "pyro",
        "stupid",
        "trending",
        "trump",
        "vrchat",
        "wip",
        "yiff",
        "zoofilia",
        "zoophilia",
        "🍆",
        "🍑",
        "💦",
        "🔞",
    ]
