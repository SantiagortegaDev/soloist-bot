"""Builds the discord.py audio source that captures Soloist's output.

Soloist has no "give me raw audio" API call — it just plays to a normal
audio output device. So we route it to a PulseAudio null-sink
(scripts/setup_pulse_sink.sh) and have ffmpeg capture that sink's monitor
live, the same way FFmpegPCMAudio normally reads a file, except here the
"file" is a continuously-updating live source.

This same code works whether Soloist runs on the same machine or on a
remote one reached through an SSH tunnel: if PULSE_SERVER is set in the
process environment (e.g. tcp:127.0.0.1:<forwarded-port>), ffmpeg's pulse
input transparently pulls audio over that tunnel instead of the local
Pulse socket. There is one Soloist device per bot process (see
docs/ARCHITECTURE.md), so setting PULSE_SERVER once at process startup
(bot/main.py) is enough — no per-call plumbing needed.
"""

from __future__ import annotations

import discord


def build_audio_source(monitor_source: str, *, volume: float = 1.0) -> discord.PCMVolumeTransformer:
    """Return a live audio source reading Soloist's PulseAudio monitor.

    monitor_source: the Pulse source name created by
        scripts/setup_pulse_sink.sh, e.g. "soloist_out.monitor".
    """
    source = discord.FFmpegPCMAudio(
        source=monitor_source,
        executable="ffmpeg",
        before_options="-nostdin -f pulse",
    )
    return discord.PCMVolumeTransformer(source, volume=volume)
