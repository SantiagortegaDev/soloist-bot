"""Slash commands for music playback."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.player import Player
from bot.spotify_client import Track


def _format_track(track: Track) -> str:
    return f"**{track.name}** — {track.artists}"


class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot, player: Player):
        self.bot = bot
        self.player = player

    async def _require_voice(self, interaction: discord.Interaction) -> discord.VoiceChannel | None:
        if interaction.user.voice and interaction.user.voice.channel:
            return interaction.user.voice.channel
        await interaction.response.send_message(
            "Join a voice channel first.", ephemeral=True
        )
        return None

    @app_commands.command(description="Search and play a track from Spotify")
    @app_commands.describe(query="Song name / artist to search for")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        channel = await self._require_voice(interaction)
        if channel is None:
            return

        await interaction.response.defer()
        results = await self.player.search(query, limit=1)
        if not results:
            await interaction.followup.send(f"No results for `{query}`.")
            return

        track = results[0]
        await self.player.join(channel)
        self.player.text_channel = interaction.channel
        await self.player.play_track(track)
        await interaction.followup.send(f"Playing {_format_track(track)}")

    @app_commands.command(description="Search Spotify without playing")
    @app_commands.describe(query="Song name / artist to search for")
    async def search(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer(ephemeral=True)
        results = await self.player.search(query, limit=5)
        if not results:
            await interaction.followup.send(f"No results for `{query}`.")
            return
        lines = [f"{i+1}. {_format_track(t)}" for i, t in enumerate(results)]
        await interaction.followup.send("\n".join(lines))

    @app_commands.command(description="Add a track to the Soloist queue")
    @app_commands.describe(query="Song name / artist to search for")
    async def queue(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()
        results = await self.player.search(query, limit=1)
        if not results:
            await interaction.followup.send(f"No results for `{query}`.")
            return
        track = results[0]
        await self.player.queue_track(track)
        await interaction.followup.send(f"Queued {_format_track(track)}")

    @app_commands.command(description="Pause playback")
    async def pause(self, interaction: discord.Interaction) -> None:
        await self.player.pause()
        await interaction.response.send_message("Paused.")

    @app_commands.command(description="Resume playback")
    async def resume(self, interaction: discord.Interaction) -> None:
        await self.player.resume()
        await interaction.response.send_message("Resumed.")

    @app_commands.command(description="Skip to the next track")
    async def skip(self, interaction: discord.Interaction) -> None:
        await self.player.skip()
        await interaction.response.send_message("Skipped.")

    @app_commands.command(description="Show the currently playing track")
    async def nowplaying(self, interaction: discord.Interaction) -> None:
        track = self.player.now_playing
        if not track:
            await interaction.response.send_message("Nothing is playing.")
            return
        await interaction.response.send_message(_format_track(track))

    @app_commands.command(description="Set playback volume (0-100)")
    @app_commands.describe(level="Volume from 0 to 100")
    async def volume(self, interaction: discord.Interaction, level: app_commands.Range[int, 0, 100]) -> None:
        await self.player.set_volume(level)
        await interaction.response.send_message(f"Volume set to {level}.")

    @app_commands.command(description="Join your current voice channel")
    async def join(self, interaction: discord.Interaction) -> None:
        channel = await self._require_voice(interaction)
        if channel is None:
            return
        await self.player.join(channel)
        self.player.text_channel = interaction.channel
        await interaction.response.send_message(f"Joined {channel.mention}.")

    @app_commands.command(description="Leave the voice channel")
    async def leave(self, interaction: discord.Interaction) -> None:
        await self.player.leave()
        await interaction.response.send_message("Left the voice channel.")


async def setup(bot: commands.Bot) -> None:
    player: Player = bot.player  # type: ignore[attr-defined]
    await bot.add_cog(MusicCog(bot, player))
