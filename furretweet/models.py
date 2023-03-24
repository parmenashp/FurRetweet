import tweepy.asynchronous as tweepy
import tweepy.errors as tweepy_errors
from pydantic import BaseModel, Field
from datetime import datetime
from loguru import logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from furretweet.filters import Filter


class PublicMetricsUser(BaseModel):
    followers_count: int
    following_count: int
    tweet_count: int
    listed_count: int


class User(BaseModel):
    id: int
    username: str
    name: str
    verified: bool
    verified_type: str
    public_metrics: PublicMetricsUser
    created_at: datetime


class Media(BaseModel):
    media_key: str
    type: str


class PublicMetrics(BaseModel):
    retweet_count: int
    reply_count: int
    like_count: int
    quote_count: int
    impression_count: int


class Includes(BaseModel):
    users: list[User]
    media: list[Media]


class Tweet(BaseModel):
    id: int
    text: str
    author_id: int
    created_at: datetime
    public_metrics: PublicMetrics
    attachments: dict | None
    referenced_tweets: list[dict] | None
    entities: dict | None
    edit_history_tweet_ids: list[int]
    possibly_sensitive: bool | None


class StreamResponse:
    def __init__(
        self, *, client: tweepy.AsyncClient, tweet: Tweet, includes: Includes, errors: list[dict]
    ) -> None:
        self.client = client
        self.tweet = tweet
        self.includes = includes
        self.errors = errors

    def process_filters(self, filters: list["Filter"]) -> list["Filter"]:
        failed_filters = []
        for f in filters:
            if not f.filter(self):
                failed_filters.append(f)
        return failed_filters

    @property
    def author(self) -> User:
        return self.includes.users[0]

    async def retweet(self) -> None:
        await self.client.retweet(self.tweet.id)

    def __str__(self) -> str:
        return f"(https://twitter.com/_/status/{self.tweet.id}) @{self.author.username}: {self.tweet.text}"
