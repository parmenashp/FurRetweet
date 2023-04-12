import pytest
from datetime import datetime, timezone, timedelta
from furretweet.filters import (
    MinimumFollowersFilter,
    NsfwFilter,
    MinimumAccountAgeFilter,
    MaximumNewLinesFilter,
    FursuitFridayOnlyFilter,
    MediaFilter,
    MaximumHashtagsFilter,
    BannedTermsFilter,
)
from freezegun import freeze_time


def test_minimum_followers_filter(mock_response):
    mock_response.author.public_metrics.followers_count = 650
    min_followers_filter = MinimumFollowersFilter(min_followers=400)
    assert min_followers_filter.filter(mock_response)
    assert min_followers_filter.details == {"min_followers": 400, "followers_count": 650}

    mock_response.author.public_metrics.followers_count = 450
    min_followers_filter = MinimumFollowersFilter(min_followers=500)
    assert not min_followers_filter.filter(mock_response)
    assert min_followers_filter.details == {"min_followers": 500, "followers_count": 450}


def test_nsfw_filter(mock_response):
    nsfw_filter = NsfwFilter()

    mock_response.tweet.possibly_sensitive = False
    assert nsfw_filter.filter(mock_response)

    mock_response.tweet.possibly_sensitive = True
    assert not nsfw_filter.filter(mock_response)


def test_minimum_account_age_filter(mock_response):
    initial_datetime = datetime(year=2010, month=7, day=12, hour=15, minute=6, second=3)

    with freeze_time(initial_datetime):
        mock_response.author.created_at = datetime.now(tz=timezone.utc) - timedelta(days=200)
        min_account_age_filter = MinimumAccountAgeFilter(min_days=50)
        assert min_account_age_filter.filter(mock_response)
        assert min_account_age_filter.details == {
            "min_days": 50,
            "account_created_at": datetime.now(tz=timezone.utc) - timedelta(days=200),
            "checked_at": datetime.now(tz=timezone.utc),
        }

        mock_response.author.created_at = datetime.now(tz=timezone.utc) - timedelta(days=5)
        min_account_age_filter = MinimumAccountAgeFilter(min_days=50)
        assert not min_account_age_filter.filter(mock_response)
        assert min_account_age_filter.details == {
            "min_days": 50,
            "account_created_at": datetime.now(tz=timezone.utc) - timedelta(days=5),
            "checked_at": datetime.now(tz=timezone.utc),
        }


def test_maximum_new_lines_filter(mock_response):
    max_new_lines_filter = MaximumNewLinesFilter(max=3)

    mock_response.tweet.text = "line\nline2\nline3\nline4"
    assert max_new_lines_filter.filter(mock_response)
    assert max_new_lines_filter.details == {"max_new_lines": 3, "new_lines": 3}

    mock_response.tweet.text = "line\nline2\nline3\nline4\nline5"
    assert not max_new_lines_filter.filter(mock_response)
    assert max_new_lines_filter.details == {"max_new_lines": 3, "new_lines": 4}


def test_fursuit_friday_only_filter(mock_response):
    fursuit_friday_only_filter = FursuitFridayOnlyFilter()

    mock_response.tweet.text = "test"
    assert fursuit_friday_only_filter.filter(mock_response)

    mock_response.tweet.text = "#FursuitFriday"
    assert not fursuit_friday_only_filter.filter(mock_response)


def test_media_filter(mock_response):
    media_filter = MediaFilter()

    mock_response.includes.media = [{"media_key": "3_1517533153853902848", "type": "photo"}]
    assert media_filter.filter(mock_response)

    mock_response.includes.media = []
    assert not media_filter.filter(mock_response)


def test_maximum_hashtags_filter(mock_response):
    max_hashtags_filter = MaximumHashtagsFilter(max=2)
    assert max_hashtags_filter.filter(mock_response)

    mock_response.tweet.entities["hashtags"] = [{"text": "test1"}, {"text": "test2"}]
    assert max_hashtags_filter.filter(mock_response)
    assert max_hashtags_filter.details == {"max_hashtags": 2, "hashtags_count": 2}

    mock_response.tweet.entities["hashtags"] = [
        {"text": "test1"},
        {"text": "test2"},
        {"text": "test3"},
    ]
    assert not max_hashtags_filter.filter(mock_response)
    assert max_hashtags_filter.details == {"max_hashtags": 2, "hashtags_count": 3}


def test_banned_terms_filter(mock_response):
    banned_terms_filter = BannedTermsFilter()

    banned_terms_filter.banned_words = ["crypto", "nft", "kill"]

    mock_response.tweet.text = "Hello world!"
    assert banned_terms_filter.filter(mock_response)
    assert banned_terms_filter.details == {"banned_words": []}

    # Test case when filter should exclude the tweet
    mock_response.tweet.text = "Hello world! Here is some crypto."
    assert not banned_terms_filter.filter(mock_response)
    assert banned_terms_filter.details == {"banned_words": ["crypto"]}

    # Test case when filter should exclude the tweet with case-insensitive matching
    mock_response.tweet.text = "Hello world! What about Crypto?"
    assert not banned_terms_filter.filter(mock_response)
    assert banned_terms_filter.details == {"banned_words": ["crypto"]}

    # Test case when filter should exclude the tweet with multiple banned words
    mock_response.tweet.text = "Hello world! Kill people and buy NFT and crypto."
    assert not banned_terms_filter.filter(mock_response)
    # The order of the banned words is not guaranteed
    assert all(
        word in banned_terms_filter.details["banned_words"] for word in ["crypto", "nft", "kill"]
    )
