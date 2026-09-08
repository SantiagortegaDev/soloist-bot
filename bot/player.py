"""Bridges Soloist (control + audio) with a Discord voice connection.

There is one Soloist device per bot process (a single Premium account can
only power one Spotify Connect session), so there is a single shared Player
rather than one per guild. Any guild's commands act on that one listening
session; the currently-connected voice channel is where the audio goes.
"""

from __future__ import annotations

import logging

import discord

from bot.audio_source import build_audio_source
from bot.soloist_client import SoloistClient
from bot.spotify_client import SpotifyClient, Track

logger = logging.getLogger(__name__)


class Player:
    def __init__(
        self,
        soloist: SoloistClient,
        spotify: SpotifyClient,
        pulse_monitor: str,
    ):
        self.soloist = soloist
        self.spotify = spotify
        self._pulse_monitor = pulse_monitor
        self.voice_client: discord.VoiceClient | None = None
        self.now_playing: Track | None = None
        self.text_channel: discord.abc.Messageable | None = None

        self.soloist.on_event("track_changed", self._on_track_changed)
        self.soloist.on_event("playback_changed", self._on_playback_changed)

    async def join(self, channel: discord.VoiceChannel) -> None:
        if self.voice_client and self.voice_client.channel == channel:
            return
        if self.voice_client:
            await self.voice_client.move_to(channel)
        else:
            self.voice_client = await channel.connect()
        self._start_capture()

    async def leave(self) -> None:
        if self.voice_client:
            await self.voice_client.disconnect(force=True)
            self.voice_client = None

    def _start_capture(self) -> None:
        if not self.voice_client:
            return
        if self.voice_client.is_playing():
            self.voice_client.stop()
        source = build_audio_source(self._pulse_monitor)
        self.voice_client.play(source, after=self._on_capture_ended)

    def _on_capture_ended(self, error: Exception | None) -> None:
        if error:
            logger.warning("Audio capture ended with error: %s", error)

    async def search(self, query: str, limit: int = 5) -> list[Track]:
        return await self.spotify.search_tracks(query, limit=limit)

    async def play_track(self, track: Track) -> None:
        await self.soloist.play(uri=track.uri)
        self.now_playing = track

    async def queue_track(self, track: Track) -> None:
        await self.soloist.add_to_queue(track.uri)

    async def pause(self) -> None:
        await self.soloist.pause()

    async def resume(self) -> None:
        await self.soloist.play()

    async def skip(self) -> None:
        await self.soloist.skip_next()

    async def set_volume(self, volume: int) -> None:
        await self.soloist.set_volume(volume)

    async def _on_track_changed(self, message: dict) -> None:
        item = message.get("item") or message.get("track")
        if item:
            self.now_playing = Track.from_api(item)
        if self.text_channel:
            await self._announce_now_playing()

    async def _on_playback_changed(self, message: dict) -> None:
        # Reserved for future play/pause status updates in the UI.
        pass

    async def _announce_now_playing(self) -> None:
        if not self.now_playing or not self.text_channel:
            return
        track = self.now_playing
        embed = discord.Embed(title="Now Playing", description=f"{track.name} — {track.artists}")
        if track.url:
            embed.url = track.url
        await self.text_channel.send(embed=embed)
