import pytest
from furretweet.models import Tweet, Includes, StreamResponse
from unittest.mock import MagicMock


@pytest.fixture
def raw_data_example():
    return {
        "data": {
            "id": "1517533170840838144",
            "possibly_sensitive": False,
            "created_at": "2022-04-22T15:57:56.000Z",
            "author_id": "166643730",
            "entities": {
                "urls": [
                    {
                        "start": 0,
                        "end": 23,
                        "url": "https://t.co/34axngukSE",
                        "expanded_url": "https://twitter.com/DonovanCarmona/status/1517533170840838144/photo/1",
                        "display_url": "pic.twitter.com/34axngukSE",
                        "media_key": "3_1517533153853902848",
                    }
                ]
            },
            "attachments": {"media_keys": ["3_1517533153853902848"]},
            "text": "https://t.co/34axngukSE",
            "public_metrics": {
                "retweet_count": 23,
                "reply_count": 2,
                "like_count": 457,
                "quote_count": 1,
                "impression_count": 0,
            },
            "edit_history_tweet_ids": ["1517533170840838144"],
        },
        "includes": {
            "media": [{"media_key": "3_1517533153853902848", "type": "photo"}],
            "users": [
                {
                    "verified": False,
                    "id": "166643730",
                    "public_metrics": {
                        "followers_count": 2547,
                        "following_count": 799,
                        "tweet_count": 43069,
                        "listed_count": 9,
                    },
                    "username": "DonovanCarmona",
                    "created_at": "2010-07-14T17:24:34.000Z",
                    "verified_type": "none",
                    "name": "Dônovan",
                }
            ],
        },
        "errors": [],
    }


@pytest.fixture
def mock_response(raw_data_example):
    tweet = Tweet.parse_obj(raw_data_example["data"])
    includes = Includes.parse_obj(raw_data_example["includes"])
    errors = []

    return StreamResponse(client=MagicMock(), tweet=tweet, includes=includes, errors=errors)  # type: ignore
