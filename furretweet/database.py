from pydantic import BaseModel, Field
from typing import TYPE_CHECKING
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

if TYPE_CHECKING:
    from furretweet.config import Config
    from furretweet.models import StreamResponse


class MongoDatabase:
    def __init__(self, config: "Config") -> None:
        self.config = config
        self.client = AsyncIOMotorClient(config.mongo.uri)
        self.db = self.client[config.mongo.database]
        self.not_retweeted_tweets_repository = NotRetweetedTweetsRepository(
            collection=self.db[self.config.mongo.not_retweeted_tweets_collection]
        )


class FailedFilter(BaseModel):
    filter_name: str
    details: dict


class NotRetweetedTweet(BaseModel):
    id: str = Field(alias="_id")
    text: str
    author_id: str
    created_at: datetime
    limit_reached: bool
    failed_filters: list[FailedFilter]


class NotRetweetedTweetsRepository:
    def __init__(self, collection) -> None:
        self.collection = collection

    async def add(self, response: "StreamResponse") -> None:
        tweet = NotRetweetedTweet(
            _id=str(response.tweet.id),
            text=response.tweet.text,
            author_id=str(response.author.id),
            created_at=response.tweet.created_at,
            limit_reached=response.limit_reached,
            failed_filters=[
                FailedFilter(filter_name=filter.__class__.__name__, details=filter.details)
                for filter in response.failed_filters
            ],
        )
        await self.collection.insert_one(tweet.dict(by_alias=True))
