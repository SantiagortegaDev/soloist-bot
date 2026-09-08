from __future__ import annotations

import asyncio
import json

import pytest
import websockets

from bot.soloist_client import SoloistClient


@pytest.fixture
async def fake_soloist_server():
    """A minimal fake Soloist WS server: echoes command acks and lets the
    test push arbitrary events to connected clients."""
    connected = asyncio.Queue()

    async def handler(ws):
        connected.put_nowait(ws)
        async for raw in ws:
            message = json.loads(raw)
            await ws.send(json.dumps({"type": "command_result", "command": message.get("command")}))

    server = await websockets.serve(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield f"ws://127.0.0.1:{port}", connected
    finally:
        server.close()
        await server.wait_closed()


async def test_connect_and_send_command(fake_soloist_server):
    url, _connected = fake_soloist_server
    client = SoloistClient(url, reconnect_delay=0.1)

    await client.connect()
    assert client.connected

    events = []
    client.on_event("command_result", lambda msg: events.append(msg))

    await client.play(uri="spotify:track:abc")

    await asyncio.wait_for(_wait_for(lambda: len(events) == 1), timeout=2)
    assert events[0]["command"] == "play"

    await client.close()


async def test_dispatches_track_changed_and_updates_state(fake_soloist_server):
    url, connected = fake_soloist_server
    client = SoloistClient(url, reconnect_delay=0.1)
    await client.connect()

    received = []
    client.on_event("track_changed", lambda msg: received.append(msg))

    server_ws = await connected.get()
    await server_ws.send(json.dumps({"type": "track_changed", "item": {"name": "Song"}}))

    await asyncio.wait_for(_wait_for(lambda: len(received) == 1), timeout=2)
    assert received[0]["item"]["name"] == "Song"
    assert client.last_state["item"]["name"] == "Song"

    await client.close()


async def _wait_for(predicate, interval=0.02):
    while not predicate():
        await asyncio.sleep(interval)
