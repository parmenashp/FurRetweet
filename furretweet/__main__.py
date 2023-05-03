import tweepy.asynchronous as tweepy
from tweepy import StreamRule
import asyncio
from loguru import logger
from furretweet.stream import FurStream
from furretweet.config import config
from furretweet.database import MongoDatabase
from furretweet.telegram import bot as telegram_bot
from furretweet.tweepy import client as tweepy_client

STREAM_EXPANSIONS = "author_id,attachments.media_keys"
STREAM_TWEET_FIELDS = "author_id,created_at,entities,public_metrics,possibly_sensitive"
STREAM_USER_FIELDS = "created_at,public_metrics,username,verified,verified_type"

STREAM_RULES = [
    StreamRule(
        value="(#FursuitFriday OR @FurRetweet) has:media -is:retweet -is:reply -is:nullcast",
        tag="FurretweetRules",
    )
]


class FurRetweet:
    def __init__(
        self,
    ):
        self.config = config
        self.client = tweepy_client
        self.mongo = MongoDatabase(self.config)
        self.stream = FurStream(bearer_token=self.config.twitter.bearer_token, furretweet=self)
        self._stream_task: asyncio.Task | None = None

    async def start(self):
        logger.info("Starting FurRetweet")
        await self._start_stream()

    async def _setup_stream_filter(self):
        # Check if rule already exists, if not add it
        rules = await self.stream.get_rules()
        # await self.stream.delete_rules(rules.data)  # type: ignore
        if rules.data is None:  # type: ignore
            logger.info("No stream rules found, adding new rules")
            await self.stream.add_rules(add=STREAM_RULES)
            return
        logger.info("Stream rules found")

    async def _start_stream(self):
        logger.debug(f"Stream Rules: {STREAM_RULES}")
        await self._setup_stream_filter()
        logger.info("Starting stream")
        self._stream_task = await self.stream.filter(
            expansions=STREAM_EXPANSIONS,
            tweet_fields=STREAM_TWEET_FIELDS,
            user_fields=STREAM_USER_FIELDS,
        )


furretweet = FurRetweet()

asyncio.run(furretweet.start())
