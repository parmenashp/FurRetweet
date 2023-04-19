from typing import Any
import pytest
import json
from furretweet.filters import MinimumFollowersFilter
from furretweet.stream import FurStream, StreamResponse
from unittest.mock import MagicMock, AsyncMock
from tweepy.errors import TooManyRequests, HTTPException


@pytest.fixture
def mock_furretweet():
    furretweet = MagicMock()
    furretweet.client = MagicMock()
    return furretweet


@pytest.fixture
def fur_stream(mock_furretweet: MagicMock):
    bearer_token = "test_bearer_token"
    return FurStream(bearer_token=bearer_token, furretweet=mock_furretweet)


@pytest.fixture
def mock_stream_response():
    return MagicMock()


@pytest.mark.asyncio
async def test_on_data(fur_stream: FurStream, raw_data_example: dict[str, Any]):
    # Mock on_response method to not call the real method
    fur_stream.on_response = AsyncMock()

    # Load raw_data from the example
    raw_data = json.dumps(raw_data_example)

    await fur_stream.on_data(raw_data)

    # Check if on_response was called with a StreamResponse object
    fur_stream.on_response.assert_called_once()
    assert isinstance(fur_stream.on_response.call_args.args[0], StreamResponse)


@pytest.mark.asyncio
async def test_on_response(fur_stream: FurStream, mock_response: StreamResponse):
    # Check if retweet was called with a StreamResponse object with no failed filters
    fur_stream.retweet = AsyncMock()
    mock_response.process_filters = MagicMock()
    mock_response.process_filters.return_value = []

    await fur_stream.on_response(mock_response)

    mock_response.process_filters.assert_called_once_with(fur_stream.filters)
    fur_stream.retweet.assert_called_once_with(mock_response)

    # Check if on_failed_filters was called with a StreamResponse object with failed filters
    fur_stream.filters = [MinimumFollowersFilter(10000)]
    mock_response.process_filters.return_value = [fur_stream.filters[0]]
    fur_stream.on_failed_filters = AsyncMock()

    await fur_stream.on_response(mock_response)

    mock_response.process_filters.assert_called_with(fur_stream.filters)
    fur_stream.on_failed_filters.assert_called_once_with(mock_response)


@pytest.mark.asyncio
async def test_on_failed_filters(fur_stream: FurStream, mock_stream_response: MagicMock):
    # Mock add method of not_retweeted_tweets_repository
    fur_stream.furretweet.mongo.not_retweeted_tweets_repository.add = AsyncMock()

    await fur_stream.on_failed_filters(mock_stream_response)

    # Check if add method was called with mock_stream_response
    fur_stream.furretweet.mongo.not_retweeted_tweets_repository.add.assert_called_once_with(
        mock_stream_response
    )


@pytest.mark.asyncio
async def test_on_rate_limit_exceeded(fur_stream: FurStream, mock_stream_response: MagicMock):
    # Mock add method of not_retweeted_tweets_repository
    fur_stream.furretweet.mongo.not_retweeted_tweets_repository.add = AsyncMock()

    await fur_stream.on_rate_limit_exceeded(mock_stream_response)

    # Check if add method was called with mock_stream_response
    fur_stream.furretweet.mongo.not_retweeted_tweets_repository.add.assert_called_once_with(
        mock_stream_response
    )


@pytest.mark.asyncio
async def test_retweet_success(fur_stream: FurStream, mock_stream_response: MagicMock):
    fur_stream.rate_limit_handler.is_limit_exceeded = lambda: False
    fur_stream.rate_limit_handler.populated = True
    mock_stream_response.retweet = AsyncMock()
    fur_stream.rate_limit_handler.update_limits = MagicMock()

    await fur_stream.retweet(mock_stream_response)

    mock_stream_response.retweet.assert_called_once()
    fur_stream.rate_limit_handler.update_limits.assert_called_once_with(
        mock_stream_response.retweet.return_value.headers
    )


@pytest.mark.asyncio
async def test_retweet_limit_exceeded(fur_stream: FurStream, mock_stream_response: MagicMock):
    fur_stream.rate_limit_handler.is_limit_exceeded = lambda: False
    fur_stream.rate_limit_handler.populated = True
    mock_stream_response.retweet = AsyncMock()
    fur_stream.rate_limit_handler.update_limits = MagicMock()
    fur_stream.on_rate_limit_exceeded = AsyncMock()

    await fur_stream.retweet(mock_stream_response)

    mock_stream_response.retweet.assert_not_called()
    fur_stream.rate_limit_handler.update_limits.assert_not_called()
    fur_stream.on_rate_limit_exceeded.assert_called_once_with(mock_stream_response)


@pytest.mark.asyncio
async def test_retweet_too_many_requests(fur_stream: FurStream, mock_stream_response: MagicMock):
    fur_stream.rate_limit_handler.is_limit_exceeded = lambda: False
    fur_stream.rate_limit_handler.populated = True
    fur_stream.rate_limit_handler.update_limits = MagicMock()
    fur_stream.on_rate_limit_exceeded = AsyncMock()
    mock_stream_response.retweet = AsyncMock(
        side_effect=TooManyRequests(response=MagicMock(headers={}))
    )

    await fur_stream.retweet(mock_stream_response)

    mock_stream_response.retweet.assert_called_once()
    fur_stream.rate_limit_handler.update_limits.assert_called_once()
    fur_stream.on_rate_limit_exceeded.assert_called_once_with(mock_stream_response)


@pytest.mark.asyncio
async def test_retweet_http_exception(fur_stream: FurStream, mock_stream_response: MagicMock):
    fur_stream.rate_limit_handler.is_limit_exceeded = lambda: False
    fur_stream.rate_limit_handler.populated = True
    fur_stream.rate_limit_handler.update_limits = MagicMock()
    mock_stream_response.retweet = AsyncMock(side_effect=HTTPException(response=MagicMock()))

    await fur_stream.retweet(mock_stream_response)

    mock_stream_response.retweet.assert_called_once()
    fur_stream.rate_limit_handler.update_limits.assert_not_called()
