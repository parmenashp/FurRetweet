import tweepy.asynchronous as tweepy
from tweepy import StreamRule
import asyncio
from loguru import logger
from furretweet.stream import FurStream
from furretweet.config import Config

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
    def __init__(self, *, config: Config, client: tweepy.AsyncClient, stream: FurStream):
        self.config = config
        self.stream = stream
        self._stream_task: asyncio.Task | None = None

    async def start(self):
        logger.info("Starting FurRetweet")
        await self.start_stream()

    async def setup_stream_filter(self):
        # Check if rule already exists, if not add it
        rules = await self.stream.get_rules()
        # await self.stream.delete_rules(rules.data)  # type: ignore
        if rules.data is None:  # type: ignore
            logger.info("No stream rules found, adding new rules")
            await self.stream.add_rules(add=STREAM_RULES)
            return
        logger.info("Stream rules found")

    async def start_stream(self):
        logger.debug(f"Stream Rules: {STREAM_RULES}")
        await self.setup_stream_filter()
        logger.info("Starting stream")
        self._stream_task = await self.stream.filter(
            expansions=STREAM_EXPANSIONS,
            tweet_fields=STREAM_TWEET_FIELDS,
            user_fields=STREAM_USER_FIELDS,
        )


config = Config()
client = tweepy.AsyncClient(
    consumer_key=config.twitter.consumer_key,
    consumer_secret=config.twitter.consumer_secret,
    access_token=config.twitter.access_token,
    access_token_secret=config.twitter.access_token_secret,
    wait_on_rate_limit=False,
)
stream = FurStream(bearer_token=config.twitter.bearer_token, client=client)
furretweet = FurRetweet(config=config, client=client, stream=stream)

asyncio.run(furretweet.start())
