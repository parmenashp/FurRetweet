from dataclasses import dataclass
import os


@dataclass(frozen=True)
class TwitterConfig:
    consumer_key: str = os.environ["TWITTER_CONSUMER_KEY"]
    consumer_secret: str = os.environ["TWITTER_CONSUMER_SECRET"]
    access_token: str = os.environ["TWITTER_ACCESS_TOKEN"]
    access_token_secret: str = os.environ["TWITTER_ACCESS_TOKEN_SECRET"]
    bearer_token: str = os.environ["TWITTER_BEARER_TOKEN"]
    whitelist_list_id = 1474582057816834053
    blacklist_list_id = 1474581944432222210
    bot_account_id = 965641664487415809


@dataclass(frozen=True)
class MongoConfig:
    uri: str = os.environ["MONGO_URI"]
    database: str = "furretweet"
    not_retweeted_tweets_collection: str = "not_retweeted_tweets"


@dataclass(frozen=True)
class TelegramConfig:
    token: str = os.environ["TELEGRAM_TOKEN"]
    feed_channel_id: int = -498308406


@dataclass(frozen=True)
class Config:
    twitter = TwitterConfig()
    mongo = MongoConfig()
    telegram = TelegramConfig()


config = Config()
