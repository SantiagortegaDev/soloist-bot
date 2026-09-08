from __future__ import annotations

from bot.spotify_client import SpotifyClient


def _track_payload(uri="spotify:track:123", name="Test Song"):
    return {
        "uri": uri,
        "name": name,
        "artists": [{"name": "Test Artist"}],
        "album": {"name": "Test Album"},
        "duration_ms": 210000,
        "external_urls": {"spotify": "https://open.spotify.com/track/123"},
    }


class _FakeResponse:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._payload = payload

    async def json(self):
        return self._payload

    async def text(self):
        return str(self._payload)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeSession:
    """Stands in for aiohttp.ClientSession, recording calls and returning
    scripted responses, so the real client/token/search HTTP logic can be
    tested without any network access."""

    def __init__(self):
        self.post_calls = []
        self.get_calls = []
        self.token_response = {"access_token": "fake-token", "expires_in": 3600}
        self.search_response = {"tracks": {"items": [_track_payload()]}}

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        return _FakeResponse(200, self.token_response)

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return _FakeResponse(200, self.search_response)


async def test_search_tracks_returns_parsed_results():
    session = _FakeSession()
    client = SpotifyClient("id", "secret", session)

    results = await client.search_tracks("test song")

    assert len(results) == 1
    track = results[0]
    assert track.uri == "spotify:track:123"
    assert track.name == "Test Song"
    assert track.artists == "Test Artist"
    assert track.album == "Test Album"
    assert len(session.post_calls) == 1  # one token fetch
    assert len(session.get_calls) == 1


async def test_search_tracks_empty_query_returns_empty_without_http():
    session = _FakeSession()
    client = SpotifyClient("id", "secret", session)

    results = await client.search_tracks("   ")

    assert results == []
    assert session.get_calls == []


async def test_token_is_cached_between_calls():
    session = _FakeSession()
    client = SpotifyClient("id", "secret", session)

    await client.search_tracks("a")
    await client.search_tracks("b")

    assert len(session.post_calls) == 1  # token fetched once, reused
    assert len(session.get_calls) == 2
