# soloist-bot

A self-hosted, open-source Discord music bot that plays the **real Spotify
catalog** in a voice channel — powered by [discord.py](https://discordpy.readthedocs.io/)
for Discord and [Spotify Soloist](https://developer.spotify.com/documentation/soloist)
(Spotify's own headless Connect client) for actual playback on a Premium
account.

Every self-hoster provides their own Discord bot token, Spotify Web API app,
Soloist API key, and Premium account — nothing is shared between installs.

**Runs on one dedicated server only** (a small VPS, home server, or
Raspberry Pi) — the bot, `soloist`, and PulseAudio all run together there.
This is deliberate: Soloist's audio only ever exists as a virtual sink, so
there's no dependency on (or conflict with) real audio hardware, and
nothing needs to be exposed over a network. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full picture (Spotify
Web API for search, Soloist + PulseAudio + ffmpeg for audio into the voice
channel) and why it's one server only.

## Quick start

```bash
git clone https://github.com/SantiagortegaDev/soloist-bot.git
cd soloist-bot
./install.sh          # checks dependencies, creates .venv, walks you through .env
source .venv/bin/activate
python3 main.py
```

`install.sh` checks for python3.11+/ffmpeg/PulseAudio, installs the Python
dependencies into `.venv`, and interactively writes `.env` with your Discord
token and Spotify credentials (leave a field blank to fill it in later by
hand). It's safe to re-run at any time.

You'll still need to get those credentials first, and set up Spotify
Soloist (the piece that actually plays audio) — see:

1. [docs/AUTH.md](docs/AUTH.md) — Discord token, Spotify Web API app,
   Soloist API key + Premium pairing.
2. [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — setting up the dedicated
   server (PulseAudio sink, running Soloist, systemd services).

Once `.env` is filled in, start (or restart) the bot with:

```bash
source .venv/bin/activate && python3 main.py
```

(equivalent to `python -m bot.main`, kept as an alternative if you prefer
running it as a module).

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
