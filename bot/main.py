"""Entrypoint: wires config, Spotify/Soloist clients and the Discord bot."""

from __future__ import annotations

import asyncio
import logging
import os

import aiohttp
import discord
from discord.ext import commands

from bot.config import Config, ConfigError, load_config
from bot.player import Player
from bot.soloist_client import SoloistClient
from bot.spotify_client import SpotifyClient

logger = logging.getLogger("soloist_bot")

INITIAL_EXTENSIONS = ("bot.cogs.music", "bot.cogs.admin")


def _build_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.voice_states = True
    intents.message_content = False
    return commands.Bot(command_prefix="!", intents=intents)


async def _async_main(config: Config) -> None:
    if config.pulse_server:
        # A single Soloist device serves the whole process (see
        # docs/ARCHITECTURE.md), so setting this once here is enough to
        # make ffmpeg's pulse input transparently follow the SSH tunnel.
        os.environ["PULSE_SERVER"] = config.pulse_server

    bot = _build_bot()

    async with aiohttp.ClientSession() as session:
        spotify = SpotifyClient(config.spotify_client_id, config.spotify_client_secret, session)
        soloist = SoloistClient(config.soloist_ws_url)
        player = Player(soloist, spotify, config.pulse_monitor)
        bot.player = player  # type: ignore[attr-defined]

        @bot.event
        async def on_ready() -> None:
            logger.info("Logged in as %s", bot.user)
            await bot.tree.sync()

        for extension in INITIAL_EXTENSIONS:
            await bot.load_extension(extension)

        soloist.start()
        try:
            await bot.start(config.discord_token)
        finally:
            await soloist.close()


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        config = load_config()
    except ConfigError as exc:
        logger.error(str(exc))
        raise SystemExit(1) from exc

    asyncio.run(_async_main(config))


if __name__ == "__main__":
    run()
