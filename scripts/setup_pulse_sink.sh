#!/usr/bin/env bash
# Creates a PulseAudio null-sink for Spotify Soloist to play into, instead
# of real speakers, so ffmpeg can capture it and forward it to Discord.
#
# Run this once per boot (or wire it into your Soloist systemd unit) on the
# machine that runs `soloist`.
#
# Usage: scripts/setup_pulse_sink.sh [sink_name] [pulse_tcp_port]
set -euo pipefail

SINK_NAME="${1:-soloist_out}"
PULSE_TCP_PORT="${2:-4713}"

if ! command -v pactl >/dev/null 2>&1; then
    echo "pactl not found — install pulseaudio-utils (or pipewire-pulse)." >&2
    exit 1
fi

if ! pactl list short sinks | grep -q "\b${SINK_NAME}\b"; then
    pactl load-module module-null-sink \
        sink_name="${SINK_NAME}" \
        sink_properties=device.description="Soloist_output"
    echo "Created null sink: ${SINK_NAME}"
else
    echo "Null sink ${SINK_NAME} already exists."
fi

# Enable network access to Pulse ONLY on localhost. This is what lets an
# SSH tunnel (ssh -R PULSE_PORT:127.0.0.1:PULSE_PORT) forward audio to a
# remote bot process. Never bind this to a public interface.
if ! pactl list short modules | grep -q "module-native-protocol-tcp.*port=${PULSE_TCP_PORT}"; then
    pactl load-module module-native-protocol-tcp \
        listen=127.0.0.1 port="${PULSE_TCP_PORT}" auth-anonymous=1
    echo "Enabled Pulse TCP module on 127.0.0.1:${PULSE_TCP_PORT}"
else
    echo "Pulse TCP module already listening on port ${PULSE_TCP_PORT}."
fi

echo
echo "Point Soloist's audio output at the '${SINK_NAME}' sink, and set in your .env:"
echo "  SOLOIST_PULSE_MONITOR=${SINK_NAME}.monitor"
