import pytest
from unittest.mock import MagicMock, AsyncMock
from pydantic import ValidationError
from furretweet.filters import NsfwFilter, BannedTermsFilter
from furretweet.database import (
    MongoDatabase,
    NotRetweetedTweetsRepository,
    NotRetweetedTweet,
    FailedFilter,
)
from datetime import datetime, timezone


# This fixture is a sample configuration
@pytest.fixture
def sample_config():
    return MagicMock(
        mongo=MagicMock(
            uri="mongodb://localhost:27017",
            database="test_db",
            not_retweeted_tweets_collection="test_collection",
        )
    )


@pytest.fixture
def mongo_database(sample_config):
    return MongoDatabase(config=sample_config)


@pytest.fixture
def not_retweeted_tweets_repository(mongo_database):
    return mongo_database.not_retweeted_tweets_repository


def test_mongo_database_initialization(sample_config):
    mongo_database = MongoDatabase(config=sample_config)

    assert mongo_database.config == sample_config
    assert mongo_database.client is not None
    assert mongo_database.db is not None
    assert isinstance(mongo_database.not_retweeted_tweets_repository, NotRetweetedTweetsRepository)


def test_not_retweeted_tweet_model():
    data = {
        "_id": "1",
        "text": "Sample tweet text",
        "author_id": "2",
        "created_at": datetime.now(tz=timezone.utc),
        "limit_reached": False,
        "failed_filters": [
            {"filter_name": "SomeFilter", "details": {"some": "details"}},
            {"filter_name": "AnotherFilter", "details": {"another": "detail"}},
        ],
    }

    not_retweeted_tweet = NotRetweetedTweet(**data)
    assert not_retweeted_tweet.dict(by_alias=True) == data

    with pytest.raises(ValidationError):
        NotRetweetedTweet(**{**data, "failed_filters": [{"filter_name": "InvalidFilter"}]})


@pytest.mark.asyncio
async def test_not_retweeted_tweets_repository_add(mock_response, not_retweeted_tweets_repository):
    not_retweeted_tweets_repository.collection.insert_one = AsyncMock()
    banned_terms_filter = BannedTermsFilter()
    banned_terms_filter.words_found = ["banned", "words"]
    mock_response.failed_filters = [NsfwFilter(), banned_terms_filter]

    # Test adding a StreamResponse to the repository
    await not_retweeted_tweets_repository.add(mock_response)

    not_retweeted_tweets_repository.collection.insert_one.assert_called_once()
    tweet_data = not_retweeted_tweets_repository.collection.insert_one.call_args.args[0]

    assert tweet_data["_id"] == str(mock_response.tweet.id)
    assert tweet_data["text"] == mock_response.tweet.text
    assert tweet_data["author_id"] == str(mock_response.author.id)
    assert tweet_data["created_at"] == mock_response.tweet.created_at
    assert tweet_data["limit_reached"] == mock_response.limit_reached
    assert tweet_data["failed_filters"] == [
        {"filter_name": "NsfwFilter", "details": {}},
        {"filter_name": "BannedTermsFilter", "details": banned_terms_filter.details},
    ]
