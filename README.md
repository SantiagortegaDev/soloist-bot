# soloist-bot

A self-hosted, open-source Discord music bot that plays the **real Spotify
catalog** in a voice channel — powered by [discord.py](https://discordpy.readthedocs.io/)
for Discord and [Spotify Soloist](https://developer.spotify.com/documentation/soloist)
(Spotify's own headless Connect client) for actual playback on a Premium
account.

Every self-hoster provides their own Discord bot token, Spotify Web API app,
Soloist API key, and Premium account — nothing is shared between installs.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the pieces fit
together (Spotify Web API for search, Soloist + PulseAudio + ffmpeg for
audio into the voice channel).

## Quick start

1. Set up authentication — Discord token, Spotify Web API app, Soloist API
   key + Premium pairing: [docs/AUTH.md](docs/AUTH.md).
2. Deploy — same machine, or bot on a remote server with Soloist at home
   over an SSH tunnel: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
3. Install and run:

   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -e .
   cp .env.example .env   # fill in your credentials
   python -m bot.main
   ```

## Commands

- `/play <query>` — search Spotify and start playing the first result
- `/search <query>` — search without playing
- `/queue <query>` — add a track to the Soloist queue
- `/pause`, `/resume`, `/skip`, `/volume <0-100>`, `/nowplaying`
- `/join`, `/leave` — voice channel control
- `/status` — Soloist connection + voice status

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check bot
```

## License

MIT — see [LICENSE](LICENSE).
