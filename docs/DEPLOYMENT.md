# Deployment

The bot code never changes between these two setups — it always connects
to `127.0.0.1`. What differs is purely where processes run and how their
local ports get forwarded.

## Option A — same machine

Simplest setup: `soloist`, PulseAudio, and the bot all run on one machine
that also has outbound internet access (needed for the Discord gateway and
Spotify Web API anyway).

```bash
scripts/setup_pulse_sink.sh
./scripts/run_soloist.sh &     # your filled-in copy of run_soloist.sh.example
python -m bot.main
```

`.env` on this machine:

```
SOLOIST_WS_HOST=127.0.0.1
SOLOIST_WS_PORT=5710
SOLOIST_PULSE_MONITOR=soloist_out.monitor
# PULSE_SERVER left empty — uses the local Pulse socket
```

## Option B — Soloist at home, bot on a remote server, via SSH tunnel

Use this when you want the bot to stay online on a VPS, but the
Premium/Soloist audio device is a machine at home (e.g. a Raspberry Pi) that
isn't always reachable or doesn't have great uptime for a public service.

**On the home machine** (runs `soloist` + PulseAudio):

```bash
scripts/setup_pulse_sink.sh          # exposes Pulse TCP on 127.0.0.1:4713
./scripts/run_soloist.sh &           # exposes Soloist WS on 127.0.0.1:5710
```

Open a reverse SSH tunnel from the home machine to your remote server,
forwarding *both* ports to the server's own `127.0.0.1`:

```bash
ssh -N \
  -R 5710:127.0.0.1:5710 \
  -R 4713:127.0.0.1:4713 \
  you@your-remote-server
```

Keep this tunnel alive with `autossh` or a systemd unit with
`Restart=always`, for example:

```ini
# /etc/systemd/system/soloist-tunnel.service (on the home machine)
[Unit]
Description=SSH tunnel: Soloist -> remote bot server
After=network-online.target

[Service]
ExecStart=/usr/bin/autossh -M 0 -N \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -R 5710:127.0.0.1:5710 -R 4713:127.0.0.1:4713 \
  you@your-remote-server
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**On the remote server** (runs the bot):

```
SOLOIST_WS_HOST=127.0.0.1
SOLOIST_WS_PORT=5710
SOLOIST_PULSE_MONITOR=soloist_out.monitor
PULSE_SERVER=tcp:127.0.0.1:4713
```

```bash
python -m bot.main
```

From the bot's point of view this is identical to Option A — it just talks
to `127.0.0.1`. The SSH tunnel is what makes those ports real.

### Security notes

- Both the Soloist WS port and PulseAudio's TCP module are
  **unauthenticated by design**. Bind them to `127.0.0.1` on the home
  machine (never `0.0.0.0`), and let the SSH tunnel — not a firewall rule
  — be the only path to them from outside. `ssh -R` binds the forwarded
  port on the remote server's `127.0.0.1` too, unless you also pass
  `GatewayPorts` server-side; don't.
- Use SSH key auth for the tunnel, not a password.
- If the tunnel drops, the bot will keep retrying the Soloist WS connection
  (`SoloistClient` auto-reconnects) and audio capture will resume once the
  tunnel and Pulse connection are back.
