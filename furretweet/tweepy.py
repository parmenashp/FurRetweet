from tweepy.asynchronous import AsyncClient
from furretweet.config import config
import aiohttp

client = AsyncClient(
    consumer_key=config.twitter.consumer_key,
    consumer_secret=config.twitter.consumer_secret,
    access_token=config.twitter.access_token,
    access_token_secret=config.twitter.access_token_secret,
    wait_on_rate_limit=False,
    return_type=aiohttp.ClientResponse,  # type: ignore
)
