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
                     one dedicated server
        ┌──────────────────────────────────────────────┐
        │  soloist daemon  ──ws (JSON, 127.0.0.1)──▶  control: play/pause/
        │        │                                     skip/queue/volume
        │        │                                     events: track_changed
        │        └─ audio ──▶ PulseAudio null-sink "soloist_out"
        │                              │
        │                              ▼ ffmpeg -f pulse -i soloist_out.monitor
        │                     discord.py bot / VoiceClient.play()
        └──────────────────────────────┬───────────────────────┘
                                        ▼
                              Discord voice channel
```

Spotify Premium account pairing happens once, via Spotify Connect, from
the Spotify app on any device — see [docs/AUTH.md](AUTH.md).

## One dedicated server, on purpose

`soloist`, PulseAudio, and the bot **all run together on the same machine**
— see [docs/DEPLOYMENT.md](DEPLOYMENT.md). This is a deliberate choice, not
just the simple option:

- Soloist's audio never leaves the machine as real sound — it only exists
  as a virtual PulseAudio sink, so there's never a conflict with (or
  dependency on) whatever audio hardware/output device that machine has.
  A headless VPS with no sound card at all works fine.
- Soloist's WebSocket and PulseAudio's TCP module are **unauthenticated by
  design** (see Security below) — keeping everything on one box means
  nothing needs to be exposed or tunneled over a network at all.
- One process topology to document, deploy, and debug, instead of two.

## One Soloist device per bot process

A single Spotify Premium account can only drive one Spotify Connect
playback session at a time. So this bot maintains **one** `SoloistClient`
connection and **one** `Player` for the whole process — any guild's slash
commands act on that same listening session, and the audio only ever goes
to whichever voice channel the bot most recently joined. This is a
single-"room" bot by design, matching what one Soloist/Premium account can
physically do. Running multiple independent instances (their own bot
token, Spotify app, Soloist device, dedicated server, and PulseAudio sink)
is how you'd serve multiple simultaneous listening rooms.

## Security

Soloist's WebSocket API has **no authentication, TLS, or origin checks** by
design (per Spotify's own docs) — it is meant to be local-only. Likewise,
`scripts/setup_pulse_sink.sh` only ever binds PulseAudio's TCP module to
`127.0.0.1`. Since the bot, Soloist, and PulseAudio all run on the same
server and only ever talk to each other over `127.0.0.1`, neither port
needs to be reachable from outside that server at all — don't open them in
any firewall.
