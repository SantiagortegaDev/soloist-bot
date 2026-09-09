"""Async client for Spotify Soloist's local JSON WebSocket API.

Soloist exposes playback control (play/pause/skip/seek/volume/queue) and
emits state/events over a plain JSON WebSocket that Spotify's own docs say
has no built-in authentication, TLS, or origin checks — it must only ever
be reached over 127.0.0.1 (or an SSH tunnel terminating there). This client
assumes that guarantee is already satisfied by deployment (see
docs/DEPLOYMENT.md) and just speaks the protocol.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


class SoloistError(RuntimeError):
    pass


class SoloistClient:
    """Maintains a connection to Soloist's WS API with auto-reconnect.

    Usage:
        client = SoloistClient("ws://127.0.0.1:5710")
        client.on_event("track_changed", handle_track_changed)
        await client.connect()
        await client.play(uri="spotify:track:...")
    """

    def __init__(self, url: str, *, reconnect_delay: float = 3.0):
        self._url = url
        self._reconnect_delay = reconnect_delay
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._listeners: dict[str, list[EventHandler]] = {}
        self._state: dict[str, Any] = {}
        self._run_task: asyncio.Task | None = None
        self._connected = asyncio.Event()

    @property
    def connected(self) -> bool:
        return self._ws is not None and self._connected.is_set()

    @property
    def last_state(self) -> dict[str, Any]:
        return dict(self._state)

    def on_event(self, event_type: str, handler: EventHandler) -> None:
        self._listeners.setdefault(event_type, []).append(handler)

    def start(self) -> None:
        """Start the background connect/reconnect loop without waiting.

        Soloist may not be reachable yet when the bot starts (not set up,
        machine offline, SSH tunnel not up) — that shouldn't stop the bot
        from logging into Discord. The loop keeps retrying in the
        background; check `connected` (or /status) to see when it's up.
        """
        if self._run_task is None:
            self._run_task = asyncio.create_task(self._run_forever())

    async def connect(self) -> None:
        """Start the background connect/reconnect loop and wait for the
        first successful connection. Useful in tests/scripts where a
        working Soloist connection is a precondition; bot/main.py uses
        `start()` instead so it never blocks on Soloist being reachable."""
        self.start()
        await self._connected.wait()

    async def close(self) -> None:
        if self._run_task is not None:
            self._run_task.cancel()
            self._run_task = None
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        self._connected.clear()

    async def _run_forever(self) -> None:
        while True:
            try:
                async with websockets.connect(self._url) as ws:
                    self._ws = ws
                    self._connected.set()
                    logger.info("Connected to Soloist at %s", self._url)
                    await self._receive_loop(ws)
            except (ConnectionClosed, OSError) as exc:
                logger.warning("Soloist connection lost (%s), retrying...", exc)
            except asyncio.CancelledError:
                raise
            finally:
                self._ws = None
                self._connected.clear()
            await asyncio.sleep(self._reconnect_delay)

    async def _receive_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        async for raw in ws:
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Ignoring non-JSON message from Soloist: %r", raw)
                continue
            await self._dispatch(message)

    async def _dispatch(self, message: dict[str, Any]) -> None:
        event_type = message.get("type")
        if event_type in ("playback_state", "track_changed", "playback_changed"):
            self._state.update(message)

        for handler in self._listeners.get(event_type, []):
            result = handler(message)
            if asyncio.iscoroutine(result):
                await result

    async def send_command(self, command: str, **fields: Any) -> None:
        if self._ws is None:
            raise SoloistError("Not connected to Soloist")
        payload = {"type": "command", "command": command, **fields}
        await self._ws.send(json.dumps(payload))

    # --- convenience wrappers over send_command ---

    async def play(self, uri: str | None = None) -> None:
        await self.send_command("play", **({"uri": uri} if uri else {}))

    async def pause(self) -> None:
        await self.send_command("pause")

    async def skip_next(self) -> None:
        await self.send_command("skip_next")

    async def skip_prev(self) -> None:
        await self.send_command("skip_prev")

    async def seek(self, position_ms: int) -> None:
        await self.send_command("seek", position_ms=position_ms)

    async def set_volume(self, volume: int) -> None:
        volume = max(0, min(100, volume))
        await self.send_command("set_volume", volume=volume)

    async def add_to_queue(self, uri: str) -> None:
        await self.send_command("add_to_queue", uri=uri)

    async def get_queue(self, limit: int | None = None) -> None:
        await self.send_command("get_queue", **({"limit": limit} if limit else {}))

    async def get_state(self) -> None:
        await self.send_command("get_state")
