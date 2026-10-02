import asyncio
import threading
from unittest.mock import Mock

from Adapters.zigbee_sensor_adapter import ZigbeeSensorAdapter


async def test_close_during_connect_does_not_start_network_loop():
    connected, release = threading.Event(), threading.Event()
    adapter = ZigbeeSensorAdapter.__new__(ZigbeeSensorAdapter)
    adapter._name = "fake"
    adapter._stop = threading.Event()
    adapter._online = threading.Event()
    def connect(*args):
        connected.set()
        assert release.wait(2)
    adapter._client = Mock(connect=connect)
    adapter._thread = threading.Thread(target=adapter._run)
    adapter._thread.start()
    try:
        assert await asyncio.to_thread(connected.wait, 1)
        closing = asyncio.create_task(asyncio.to_thread(adapter.close))
        assert await asyncio.to_thread(adapter._stop.wait, 1)
        release.set()
        await closing
        assert not adapter._thread.is_alive()
        adapter._client.loop_forever.assert_not_called()
        adapter.close()
    finally:
        release.set()
        await asyncio.to_thread(adapter._thread.join, 2)
