"""Builds the discord.py audio source that captures Soloist's output.

Soloist has no "give me raw audio" API call — it just plays to a normal
audio output device. So we route it to a PulseAudio null-sink
(scripts/setup_pulse_sink.sh) and have ffmpeg capture that sink's monitor
live, the same way FFmpegPCMAudio normally reads a file, except here the
"file" is a continuously-updating live source.

This bot is meant to run entirely on one dedicated, headless server
alongside `soloist` and PulseAudio (see docs/DEPLOYMENT.md) — there is no
real audio hardware involved anywhere, only the null-sink, so there is
nothing to route over the network and no PULSE_SERVER to configure.
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
