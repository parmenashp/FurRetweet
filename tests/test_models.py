import pytest
from furretweet.models import StreamResponse
from furretweet.filters import BaseFilter
from unittest.mock import MagicMock, AsyncMock


class MockedTestFilter(BaseFilter):
    def __init__(self, result):
        self.result = result

    def filter(self, response: StreamResponse) -> bool:
        return self.result


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def mock_tweet():
    tweet = MagicMock()
    tweet.id = "12345"
    return tweet


@pytest.fixture
def mock_includes():
    includes = MagicMock()
    includes.users = [MagicMock()]
    return includes


@pytest.fixture
def mock_stream_response(mock_client, mock_tweet, mock_includes):
    errors = []
    return StreamResponse(
        client=mock_client, tweet=mock_tweet, includes=mock_includes, errors=errors
    )


def test_process_filters(mock_stream_response):
    filters = [MockedTestFilter(True), MockedTestFilter(False), MockedTestFilter(True)]
    failed_filters = mock_stream_response.process_filters(filters)

    assert len(failed_filters) == 1
    assert isinstance(failed_filters[0], MockedTestFilter)
    assert not failed_filters[0].result


def test_author(mock_stream_response):
    author = mock_stream_response.author
    assert author == mock_stream_response.includes.users[0]


@pytest.mark.asyncio
async def test_retweet(mock_stream_response):
    mock_stream_response.client.retweet = AsyncMock()
    await mock_stream_response.retweet()
    mock_stream_response.client.retweet.assert_called_once_with(mock_stream_response.tweet.id)


def test_url(mock_stream_response):
    url = mock_stream_response.url
    expected_url = f"https://twitter.com/{mock_stream_response.includes.users[0].username}/status/{mock_stream_response.tweet.id}"
    assert url == expected_url


def test_str_representation(mock_stream_response):
    string_representation = str(mock_stream_response)
    expected_str = f"({mock_stream_response.url}) @{mock_stream_response.includes.users[0].username}: {mock_stream_response.tweet.text}"
    assert string_representation == expected_str
