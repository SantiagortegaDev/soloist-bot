# Architecture

soloist-bot plays the **real Spotify catalog** in a Discord voice channel by
combining two things:

1. **Spotify Web API** (Client Credentials flow) — used only for catalog
   *search*, to turn `/play <query>` into a `spotify:track:...` URI. No user
   login, no Premium requirement for this part.
2. **Spotify Soloist** — Spotify's own official headless Connect client. It
   logs into a real **Premium** account via Spotify Connect pairing (never
   through this bot) and actually plays the track. Soloist exposes a local,
   unauthenticated JSON WebSocket for control (`play`, `pause`, `skip_next`,
   `seek`, `set_volume`, `add_to_queue`, ...) and events (`track_changed`,
   `playback_changed`, ...).

Soloist has no API to hand us raw audio bytes — it just plays to a normal
audio output device. So Soloist's output is routed to a **PulseAudio
null-sink**, and `ffmpeg` captures that sink's monitor live as the input to
`discord.py`'s voice player — the same mechanism `FFmpegPCMAudio` normally
uses to read a file, pointed at a live source instead.

```
Spotify Premium account
        │  Spotify Connect pairing (one-time, via the Spotify app)
        ▼
   soloist daemon  ──ws (JSON, local only)──▶  control: play/pause/skip/queue/volume
        │                                      events: track_changed/playback_changed
        └─ audio ──▶ PulseAudio null-sink "soloist_out"
                              │
                              ▼ ffmpeg -f pulse -i soloist_out.monitor
                     discord.py VoiceClient.play()
                              │
                              ▼
                     Discord voice channel
```

## One Soloist device per bot process

A single Spotify Premium account can only drive one Spotify Connect
playback session at a time. So this bot maintains **one** `SoloistClient`
connection and **one** `Player` for the whole process — any guild's slash
commands act on that same listening session, and the audio only ever goes
to whichever voice channel the bot most recently joined. This is a
single-"room" bot by design, matching what one Soloist/Premium account can
physically do. Running multiple independent instances (their own bot
token, Spotify app, Soloist device, and PulseAudio sink) is how you'd serve
multiple simultaneous listening rooms.

## Deployment topologies

Both of these use *exactly the same bot code* — see [DEPLOYMENT.md](DEPLOYMENT.md):

- **Same machine**: bot and `soloist` run side by side; the bot dials
  `127.0.0.1:<SOLOIST_WS_PORT>` and reads the local Pulse socket directly.
- **Remote bot, Soloist at home, via SSH tunnel**: `ssh -R` forwards both
  the Soloist WS port and PulseAudio's TCP port from the home machine to
  the remote server's `127.0.0.1`. The bot still only ever talks to
  `127.0.0.1` — it has no idea Soloist is elsewhere.

## Security

Soloist's WebSocket API has **no authentication, TLS, or origin checks** by
design (per Spotify's own docs) — it is meant to be local-only. Likewise
PulseAudio's TCP module is only safe with `auth-anonymous=1` when bound to
`127.0.0.1`. **Never** bind either of these to a public interface or open
their ports in a firewall; the SSH tunnel is the only sanctioned way to
reach them remotely.
