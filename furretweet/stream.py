import asyncio
import tweepy.asynchronous as tweepy
from loguru import logger
import aiohttp
import ujson
import furretweet.filters as filters
from furretweet.rate_limiter import RetweetLimitHandler
from furretweet.models import Tweet, Includes, StreamResponse
import tweepy.errors as tweepy_errors
import datetime
from zoneinfo import ZoneInfo
from furretweet.utils import log_exception

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from furretweet.__main__ import FurRetweet


class LimitReached(Exception):
    pass


class FridayChecker:
    def __init__(self):
        self.is_friday = False
        self.task: asyncio.Task | None = None

    async def start(self):
        if self.task is None:
            logger.info("Starting Friday checker")
            self.task = asyncio.create_task(self._check_if_friday())

    def _is_friday_in_timezones(self, min_tz, max_tz):
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        for timezone in (min_tz, max_tz):
            local_time = utc_now.astimezone(ZoneInfo(timezone))
            if local_time.weekday() == 4:
                return True
        return False

    @log_exception("Exception in Friday checker")
    async def _check_if_friday(self):
        # Checks if it's Friday somewhere in the world by verifying
        # if it's Friday in the earliest or latest time zones.
        # (The latest timezone is the one furthest ahead in time.)
        # If it's Friday in either of these time zones, the retweet
        # is enabled until it's Saturday in the latest timezone.
        # So, the retweet is enabled for 50 hours every Friday.
        # This is to ensure that the retweet is enabled for the entire
        # duration of Friday in every time zone!

        first_timezone = "Etc/GMT-14"
        last_timezone = "Etc/GMT+12"

        while True:
            if self._is_friday_in_timezones(first_timezone, last_timezone):
                logger.info("It's friday somewhere, retweet enabled")
                self.is_friday = True

                now_latest_tz = datetime.datetime.now(ZoneInfo(last_timezone))

                # Find the next Friday in the last timezone
                friday_latest_tz = now_latest_tz.date() + datetime.timedelta(
                    (4 - now_latest_tz.weekday()) % 7
                )

                # Calculate time until Saturday in the last timezone
                time_until_saturday_latest_tz = (
                    datetime.datetime.combine(
                        friday_latest_tz + datetime.timedelta(days=1),
                        datetime.time.min,
                        tzinfo=now_latest_tz.tzinfo,
                    )
                    - now_latest_tz
                ).total_seconds()

                logger.info(
                    f"{time_until_saturday_latest_tz:.0f} seconds until Saturday "
                    f"({(now_latest_tz + datetime.timedelta(seconds=time_until_saturday_latest_tz)).strftime('%Y-%m-%d %H:%M:%S %Z')})"
                )
                await asyncio.sleep(time_until_saturday_latest_tz)
            else:
                logger.info("It's not Friday anywhere, retweet disabled")
                self.is_friday = False

                # Calculate time until next Friday in the earliest timezone
                now_earliest_tz = datetime.datetime.now(ZoneInfo(first_timezone))
                time_until_friday_earliest_tz = (
                    datetime.datetime.combine(
                        now_earliest_tz.date()
                        + datetime.timedelta((4 - now_earliest_tz.weekday()) % 7),
                        datetime.time.min,
                        tzinfo=now_earliest_tz.tzinfo,
                    )
                    - now_earliest_tz
                ).total_seconds()
                logger.info(
                    f"Sleeping for {time_until_friday_earliest_tz:.0f} seconds until next Friday "
                    f"({(now_earliest_tz + datetime.timedelta(seconds=time_until_friday_earliest_tz)).strftime('%Y-%m-%d %H:%M:%S %Z')})"
                )
                await asyncio.sleep(time_until_friday_earliest_tz)


class FurStream(tweepy.AsyncStreamingClient):
    def __init__(self, *, bearer_token: str, furretweet: "FurRetweet"):
        super().__init__(
            bearer_token=bearer_token,
            max_retries=5,
        )
        self.furretweet = furretweet
        self.client = furretweet.client
        self.rate_limit_handler = RetweetLimitHandler()

        self.default_filters: list[filters.BaseFilter] = [
            filters.BannedTermsFilter(),
            filters.MinimumFollowersFilter(100),
            filters.NsfwFilter(),
            filters.MinimumAccountAgeFilter(30),
            filters.MediaFilter(),
            filters.MaximumHashtagsFilter(5),
            filters.MaximumNewLinesFilter(10),
            filters.FursuitFridayOnlyFilter(),
        ]

        self.whitelist_filters: list[filters.BaseFilter] = [
            filters.NsfwFilter(),
            filters.MediaFilter(),
        ]

        self.friday_checker = FridayChecker()

    async def on_connect(self):
        logger.info("Stream connected")
        await self.friday_checker.start()

    async def on_disconnect(self):
        logger.info("Stream disconnected")

    async def on_closed(self, resp: aiohttp.ClientResponse):
        logger.error(f"Stream closed by Twitter with response: {resp}")

    async def on_errors(self, errors: list[dict]):
        logger.error(f"Stream errors: {errors}")

    async def on_exception(self, exception: Exception):
        logger.exception(f"Stream exception: {exception}")

    async def on_data(self, raw_data):
        data = ujson.loads(raw_data)

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

        # I don't know why but twitter sometimes sends us a quote retweet that doesn't match
        # our stream filter, only the quoted tweet does match, so we'll just ignore this qrt.
        tweet_text_lower = tweet.text.lower()
        if not "#fursuitfriday" in tweet_text_lower and not "@furretweet" in tweet_text_lower:
            return logger.info(f"Tweet {tweet.id} does not contain #FursuitFriday or @FurRetweet")

        try:
            await self.on_response(
                StreamResponse(client=self.client, tweet=tweet, includes=includes, errors=errors)
            )
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception(f"Unhandled exception while processing stream response: {tweet}")

    async def on_response(self, response: StreamResponse):
        logger.info(f"Stream received response: {response}")

        if not self.friday_checker.is_friday:
            return logger.info("Not friday, ignoring...")

        # In the future we can cache the list of white/blacklisted users and update it every x seconds,
        # but for now we'll just fetch it every time because it will always be updated.
        # Doing this because I dont need to worry about rate limits for now, 900 requests every 15 minutes.
        if response.author.id in await self.furretweet.get_blacklist():
            return logger.info(f"Tweet {response.url} not retweeted, author is blacklisted.")

        elif response.author.id in await self.furretweet.get_whitelist():
            logger.info(f"Tweet {response.url} author is whitelisted!")
            failed_filters = response.process_filters(self.whitelist_filters)

        else:
            failed_filters = response.process_filters(self.default_filters)

        if failed_filters:
            return await self.on_failed_filters(response)
        else:
            await self.retweet(response)

    async def on_failed_filters(self, response: StreamResponse):
        await self.furretweet.mongo.not_retweeted_tweets_repository.add(response)
        logger.info(
            f"Tweet {response.url} not retweeted due to failed filters {response.failed_filters}."
        )

    async def on_rate_limit_exceeded(self, response: StreamResponse):
        response.limit_reached = True
        await self.furretweet.mongo.not_retweeted_tweets_repository.add(response)
        logger.info(
            f"Tweet {response.url} not retweeted due to rate limit. "
            f"Reset in {self.rate_limit_handler.seconds_until_reset}s"
        )

    async def retweet(self, response: StreamResponse):
        if self.rate_limit_handler.is_limit_exceeded():
            return await self.on_rate_limit_exceeded(response)

        try:
            r = await response.retweet()
            self.rate_limit_handler.update_limits(r.headers)

            r_json = await r.json()
            r_data = r_json.get("data")
            if r_data.get("retweeted") is True:
                logger.info(
                    f"Retweeted tweet {response.url}\n"
                    f"with rate limit remaining {self.rate_limit_handler.remaining} of {self.rate_limit_handler.limit} and "
                    f"reseting in {self.rate_limit_handler.seconds_until_reset}s"
                )
            else:
                logger.warning(f"Retweeting tweet {response.url} returned {r_json}.")

        except tweepy_errors.TooManyRequests as e:
            logger.debug("Got 429 Too Many Requests error from Twitter.")
            r: aiohttp.ClientResponse = e.response
            self.rate_limit_handler.update_limits(r.headers)

            if not self.rate_limit_handler.populated:
                logger.debug(
                    "Rate limit handler not populated, ignoring 429 Too Many Requests error."
                )
            else:
                logger.warning(
                    "Limit handler somehow missed the rate limit. Got 429 Too Many Requests error from Twitter. "
                    "Updating limits from response."
                )

            return await self.on_rate_limit_exceeded(response)

        except tweepy_errors.HTTPException as e:
            logger.exception(f"Error while retweeting: {e}")
