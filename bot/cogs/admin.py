"""Admin/diagnostic slash commands."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.player import Player


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot, player: Player):
        self.bot = bot
        self.player = player

    @app_commands.command(description="Show the bot's connection status")
    async def status(self, interaction: discord.Interaction) -> None:
        soloist_status = "connected" if self.player.soloist.connected else "disconnected"
        voice_status = (
            f"connected to {self.player.voice_client.channel.mention}"
            if self.player.voice_client and self.player.voice_client.channel
            else "not in a voice channel"
        )
        await interaction.response.send_message(
            f"Soloist: **{soloist_status}**\nVoice: {voice_status}",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    player: Player = bot.player  # type: ignore[attr-defined]
    await bot.add_cog(AdminCog(bot, player))
