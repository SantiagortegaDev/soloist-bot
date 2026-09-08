"""Minimal Spotify Web API client using the Client Credentials flow.

Client Credentials is app-only auth: no user ever logs in through the bot.
It's enough for catalog search/lookup, which is all this bot needs from the
Web API — actual playback happens through Spotify Soloist, not this client.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import aiohttp

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"


class SpotifyAuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class Track:
    uri: str
    name: str
    artists: str
    album: str
    duration_ms: int
    url: str

    @classmethod
    def from_api(cls, item: dict) -> Track:
        return cls(
            uri=item["uri"],
            name=item["name"],
            artists=", ".join(a["name"] for a in item.get("artists", [])),
            album=(item.get("album") or {}).get("name", ""),
            duration_ms=item.get("duration_ms", 0),
            url=(item.get("external_urls") or {}).get("spotify", ""),
        )


class SpotifyClient:
    """Handles token fetch/refresh and catalog search."""

    def __init__(self, client_id: str, client_secret: str, session: aiohttp.ClientSession):
        self._client_id = client_id
        self._client_secret = client_secret
        self._session = session
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    async def _get_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token

        async with self._session.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=aiohttp.BasicAuth(self._client_id, self._client_secret),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise SpotifyAuthError(
                    f"Spotify token request failed ({resp.status}): {body}"
                )
            payload = await resp.json()

        self._token = payload["access_token"]
        # Refresh a bit early to avoid racing the actual expiry.
        self._token_expires_at = time.monotonic() + payload.get("expires_in", 3600) - 60
        return self._token

    async def search_tracks(self, query: str, limit: int = 5) -> list[Track]:
        if not query.strip():
            return []

        token = await self._get_token()
        params = {"q": query, "type": "track", "limit": str(limit)}
        headers = {"Authorization": f"Bearer {token}"}

        async with self._session.get(
            f"{API_BASE}/search", params=params, headers=headers
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise SpotifyAuthError(f"Spotify search failed ({resp.status}): {body}")
            payload = await resp.json()

        items = (payload.get("tracks") or {}).get("items") or []
        return [Track.from_api(item) for item in items]
