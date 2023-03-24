import asyncio
import tweepy.asynchronous as tweepy
from loguru import logger
import aiohttp
import ujson as json
from furretweet import filters
from furretweet.models import Tweet, Includes, StreamResponse
import tweepy.errors as tweepy_errors
from datetime import datetime, timezone, timedelta


class FurStream(tweepy.AsyncStreamingClient):
    def __init__(self, *, bearer_token: str, client: tweepy.AsyncClient, max_retries: int = 5):
        super().__init__(
            bearer_token=bearer_token,
            max_retries=max_retries,
        )
        self.client = client
        self.filters: list[filters.BaseFilter] = [
            filters.BannedTermsFilter(),
            filters.MinimumFollowersFilter(100),
            filters.NsfwFilter(),
            filters.AccountAgeFilter(30),
            filters.MediaFilter(),
            filters.NumberHashtagsFilter(5),
            filters.MaxNewLinesFilter(10),
            filters.FursuitFridayOnlyFilter(),
        ]
        self.has_limit = True
        self.reset_delta: timedelta = timedelta(seconds=0)

    async def on_connect(self):
        logger.info("Stream connected")

    async def on_disconnect(self):
        logger.info("Stream disconnected")

    async def on_closed(self, resp: aiohttp.ClientResponse):
        logger.info(f"Stream closed by Twitter with response: {resp}")

    async def on_errors(self, errors: dict):
        logger.error(f"Stream errors: {errors}")

    async def on_exception(self, exception: Exception):
        logger.exception(f"Stream exception: {exception}")

    async def on_data(self, raw_data):
        """|coroutine|

        This is called when raw data is received from the stream.
        This method handles sending the data to other methods.

        Parameters
        ----------
        raw_data : JSON
            The raw data from the stream

        References
        ----------
        https://developer.twitter.com/en/docs/twitter-api/tweets/filtered-stream/integrate/consuming-streaming-data
        """
        data = json.loads(raw_data)

        tweet = None
        includes = {}
        errors = []

        if not "data" in data:
            return logger.warning(f"Stream received a response without data: {data}")
        if not "includes" in data:
            return logger.warning(f"Stream received a response without includes: {data}")
        if "errors" in data:
            errors = data["errors"]
            await self.on_errors(errors)

        tweet = Tweet.parse_obj(data["data"])
        includes = Includes.parse_obj(data["includes"])

        await self.on_response(
            StreamResponse(client=self.client, tweet=tweet, includes=includes, errors=errors)
        )

    async def wait_for_rate_limit(self, timedelta: timedelta):
        self.has_limit = False
        await asyncio.sleep(timedelta.total_seconds())
        self.has_limit = True

    async def on_response(self, response: StreamResponse):
        logger.debug(f"Stream received response: {response}")

        failed_filters = response.process_filters(self.filters)
        if failed_filters:
            logger.debug(
                f"Tweet https://twitter.com/_/status/{response.tweet.id} failed filters: {failed_filters}"
            )
            return
        try:
            logger.info(
                f"Tweet {response.tweet.id} from @{response.author.username} passed all filters."
            )
            if not self.has_limit:
                return logger.info(
                    f"Rate limit exceeded, waiting for reset in {self.reset_delta.seconds}s"
                )
            await response.retweet()
            logger.info(f"Retweeted tweet https://twitter.com/_/status/{response.tweet.id}")
        except tweepy_errors.TooManyRequests as e:
            resp: aiohttp.ClientResponse = e.response
            reset_at = datetime.fromtimestamp(
                int(resp.headers["x-rate-limit-reset"]), tz=timezone.utc
            )
            self.reset_delta = datetime.now(tz=timezone.utc) - reset_at
            await self.wait_for_rate_limit(self.reset_delta)
            logger.info(f"Rate limit exceeded, resetting in {self.reset_delta.seconds}s")
        except tweepy_errors.HTTPException as e:
            logger.exception(f"Error while retweeting: {e}")
