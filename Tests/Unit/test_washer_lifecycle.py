"""Real service lifecycle with an in-memory port; no BLE imports."""
import asyncio
from unittest.mock import AsyncMock

from App.washer_service import WasherService
from Ports.washer import WasherSnapshot


async def test_disconnect_then_recovery_publishes_fresh_snapshot_and_stops():
    queue = asyncio.Queue()
    received = asyncio.Queue()
    async def snapshot(**kwargs):
        value = await queue.get()
        if isinstance(value, Exception):
            raise value
        return value
    port = AsyncMock(snapshot=snapshot)
    service = WasherService(port, poll_seconds=0)
    try:
        await service.start(received.put_nowait)
        first_task = service._task
        await service.start(received.put_nowait)
        assert service._task is first_task
        for value, online, remaining in [
            (WasherSnapshot(True, 42, None), True, 42),
            (ConnectionError("fake BLE disconnect"), False, None),
            (WasherSnapshot(True, 17, None), True, 17),
        ]:
            await queue.put(value)
            state = await asyncio.wait_for(received.get(), timeout=1)
            assert (state.online, state.remaining_minutes) == (online, remaining)
    finally:
        await service.stop()
    assert first_task.done()
    assert service._task is None
    assert port.aclose.await_count >= 1
