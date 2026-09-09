#!/usr/bin/env bash
# Interactive installer for soloist-bot.
#
# - Checks for python3/pip/ffmpeg/pulseaudio and tells you what's missing
#   (and how to install it), without silently installing system packages
#   for you.
# - Creates a virtualenv and installs the bot's Python dependencies.
# - Walks you through creating .env with your own credentials.
#
# Usage: ./install.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BOLD="$(tput bold 2>/dev/null || true)"
RESET="$(tput sgr0 2>/dev/null || true)"
GREEN="$(tput setaf 2 2>/dev/null || true)"
YELLOW="$(tput setaf 3 2>/dev/null || true)"
RED="$(tput setaf 1 2>/dev/null || true)"

info()  { echo "${BOLD}==>${RESET} $*"; }
ok()    { echo "${GREEN}  ✓${RESET} $*"; }
warn()  { echo "${YELLOW}  !${RESET} $*"; }
err()   { echo "${RED}  ✗${RESET} $*"; }

MISSING=()

pkg_hint() {
    # Print a best-effort "how to install $1" line for the detected package manager.
    local pkg_apt="$1" pkg_dnf="${2:-$1}" pkg_pacman="${3:-$1}" pkg_brew="${4:-$1}"
    if command -v apt >/dev/null 2>&1; then
        echo "sudo apt install $pkg_apt"
    elif command -v dnf >/dev/null 2>&1; then
        echo "sudo dnf install $pkg_dnf"
    elif command -v pacman >/dev/null 2>&1; then
        echo "sudo pacman -S $pkg_pacman"
    elif command -v brew >/dev/null 2>&1; then
        echo "brew install $pkg_brew"
    else
        echo "(install '$pkg_apt' with your system's package manager)"
    fi
}

########################################
# 1. Check prerequisites
########################################
info "Checking prerequisites..."

if command -v python3 >/dev/null 2>&1; then
    PY_VERSION="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
    PY_MAJOR="$(python3 -c 'import sys; print(sys.version_info[0])')"
    PY_MINOR="$(python3 -c 'import sys; print(sys.version_info[1])')"
    if [ "$PY_MAJOR" -gt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge 11 ]; }; then
        ok "python3 $PY_VERSION"
    else
        err "python3 $PY_VERSION found, but 3.11+ is required."
        MISSING+=("python3.11+ — $(pkg_hint python3.11)")
    fi
else
    err "python3 not found."
    MISSING+=("python3 — $(pkg_hint python3)")
fi

if command -v ffmpeg >/dev/null 2>&1; then
    ok "ffmpeg found"
else
    err "ffmpeg not found (needed to stream Soloist's audio into Discord)."
    MISSING+=("ffmpeg — $(pkg_hint ffmpeg)")
fi

if command -v pactl >/dev/null 2>&1; then
    ok "PulseAudio (pactl) found"
else
    warn "pactl not found (needed for scripts/setup_pulse_sink.sh, on the machine that runs Soloist)."
    MISSING+=("pulseaudio-utils — $(pkg_hint pulseaudio-utils pulseaudio-utils pulseaudio pulseaudio)")
fi

if command -v soloist >/dev/null 2>&1; then
    ok "soloist found"
else
    warn "soloist not found on this machine. That's fine if it runs elsewhere (see docs/DEPLOYMENT.md) — otherwise install it from spotify/soloist."
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    echo
    warn "Missing/incomplete dependencies:"
    for item in "${MISSING[@]}"; do
        echo "    - $item"
    done
    echo
    read -r -p "Continue anyway? [y/N] " CONTINUE
    if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
        err "Aborting. Install the missing pieces above and re-run ./install.sh."
        exit 1
    fi
fi

########################################
# 2. Python virtualenv + dependencies
########################################
echo
info "Setting up the Python environment..."

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    ok "Created .venv"
else
    ok ".venv already exists"
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -e .
ok "Installed Python dependencies"

########################################
# 3. .env configuration
########################################
echo
info "Configuring .env..."

RECONFIGURE=1
if [ -f ".env" ]; then
    read -r -p ".env already exists. Reconfigure it now? [y/N] " ANSWER
    if [[ ! "$ANSWER" =~ ^[Yy]$ ]]; then
        RECONFIGURE=0
        ok "Keeping existing .env"
    fi
fi

if [ "$RECONFIGURE" -eq 1 ]; then
    echo "  Leave a field blank to fill it in later by hand in .env."
    echo

    read -r -p "  Discord bot token (docs/AUTH.md #1): " DISCORD_TOKEN
    read -r -p "  Spotify Client ID (docs/AUTH.md #2): " SPOTIFY_CLIENT_ID
    read -r -s -p "  Spotify Client Secret (hidden): " SPOTIFY_CLIENT_SECRET
    echo
    read -r -p "  Soloist WS host [127.0.0.1]: " SOLOIST_WS_HOST
    SOLOIST_WS_HOST="${SOLOIST_WS_HOST:-127.0.0.1}"
    read -r -p "  Soloist WS port [5710]: " SOLOIST_WS_PORT
    SOLOIST_WS_PORT="${SOLOIST_WS_PORT:-5710}"
    read -r -p "  Soloist Pulse monitor source [soloist_out.monitor]: " SOLOIST_PULSE_MONITOR
    SOLOIST_PULSE_MONITOR="${SOLOIST_PULSE_MONITOR:-soloist_out.monitor}"
    read -r -p "  PULSE_SERVER (leave blank unless bot runs remotely, see docs/DEPLOYMENT.md): " PULSE_SERVER

    cat > .env <<ENV_EOF
# Generated by install.sh — edit freely, never commit this file.

DISCORD_TOKEN=${DISCORD_TOKEN}

SPOTIFY_CLIENT_ID=${SPOTIFY_CLIENT_ID}
SPOTIFY_CLIENT_SECRET=${SPOTIFY_CLIENT_SECRET}

SOLOIST_WS_HOST=${SOLOIST_WS_HOST}
SOLOIST_WS_PORT=${SOLOIST_WS_PORT}

SOLOIST_PULSE_MONITOR=${SOLOIST_PULSE_MONITOR}
PULSE_SERVER=${PULSE_SERVER}
ENV_EOF

    ok "Wrote .env"

    if [ -z "$DISCORD_TOKEN" ] || [ -z "$SPOTIFY_CLIENT_ID" ] || [ -z "$SPOTIFY_CLIENT_SECRET" ]; then
        warn "Some required fields were left blank — edit .env by hand before starting the bot (see docs/AUTH.md)."
    fi
fi

########################################
# 4. Summary
########################################
echo
info "${BOLD}Done.${RESET}"
echo
echo "  Still to do on the machine running Soloist (same box or elsewhere):"
echo "    - scripts/setup_pulse_sink.sh   (creates the audio sink Soloist plays into)"
echo "    - scripts/run_soloist.sh.example (copy it, add your Soloist API key, run it)"
echo "    - Pair it once from the Spotify app (docs/AUTH.md #3)"
echo "  Remote-bot-over-SSH setup: docs/DEPLOYMENT.md"
echo
echo "  Start the bot with:"
echo "    ${BOLD}source .venv/bin/activate && python3 main.py${RESET}"
