# Deployment

soloist-bot only supports one topology: `soloist`, PulseAudio, and the bot
**all run together on one dedicated server**. See
[docs/ARCHITECTURE.md](ARCHITECTURE.md) for why — in short, it means no
real audio hardware is ever involved (so there's nothing to fight over or
misconfigure) and nothing needs to be exposed over a network.

Any always-on Linux machine works: a small VPS, a home server, a Raspberry
Pi — as long as it can stay online and reach both Discord and Spotify.

## Setup

```bash
git clone https://github.com/SantiagortegaDev/soloist-bot.git
cd soloist-bot
./install.sh
```

Then, still on that same server:

```bash
scripts/setup_pulse_sink.sh          # creates the "soloist_out" null-sink
cp scripts/run_soloist.sh.example scripts/run_soloist.sh
$EDITOR scripts/run_soloist.sh       # add your Soloist API key (docs/AUTH.md #3)
./scripts/run_soloist.sh &
```

Pair Soloist once from the Spotify app on any device on the same network
(device picker → your Soloist device name) — see
[docs/AUTH.md](AUTH.md#3-spotify-soloist-the-account-that-actually-plays-audio).
It stores the session, so you won't need to re-pair on future restarts.

`.env` (written by `install.sh`) should look like:

```
SOLOIST_WS_HOST=127.0.0.1
SOLOIST_WS_PORT=5710
SOLOIST_PULSE_MONITOR=soloist_out.monitor
```

Then start the bot:

```bash
source .venv/bin/activate && python3 main.py
```

## Keeping it running

Use a process supervisor so both `soloist` and the bot restart if they
crash or the server reboots. A minimal systemd example:

```ini
# /etc/systemd/system/soloist.service
[Unit]
Description=Spotify Soloist
After=network-online.target sound.target

[Service]
WorkingDirectory=/opt/soloist-bot
EnvironmentFile=/opt/soloist-bot/.env
ExecStart=/opt/soloist-bot/scripts/run_soloist.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/soloist-bot.service
[Unit]
Description=soloist-bot Discord bot
After=soloist.service
Requires=soloist.service

[Service]
WorkingDirectory=/opt/soloist-bot
ExecStart=/opt/soloist-bot/.venv/bin/python3 main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now soloist.service soloist-bot.service
```

## Security notes

- Soloist's WebSocket API and PulseAudio's TCP module (used by
  `scripts/setup_pulse_sink.sh`) are **unauthenticated by design**. Since
  everything runs on one server and only ever talks to `127.0.0.1`, never
  bind either to a public interface or open their ports in a firewall —
  there is no legitimate reason to reach them from outside this machine.
- Keep `.env` and `scripts/run_soloist.sh` (which holds your Soloist API
  key) out of version control — both are already covered by `.gitignore`.
