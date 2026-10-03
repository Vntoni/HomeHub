import asyncio
import threading
from unittest.mock import Mock

import pytest

from Adapters.cozytouch_heater_adapter import CozyTouchHeaterAdapter
from App.heater_service import HeaterService
from Compositions.demo import build_demo_backend


async def test_timed_out_heater_write_blocks_shared_client_and_late_steps():
    entered, release = threading.Event(), threading.Event()
    client = Mock(devices=[])
    def mode(*args):
        entered.set()
        assert release.wait(3)
        return True
    client.set_mode_program.side_effect = mode
    client.get_devices.return_value = []
    client.get_actual_temperature.return_value = 21
    client.get_device_capability.return_value = "1"
    backend = await build_demo_backend()
    backend._command_timeout = .02
    backend._heater = HeaterService({"Julia": CozyTouchHeaterAdapter(client, 1),
                                     "Juras": CozyTouchHeaterAdapter(client, 2)})
    results = []
    backend.heaterSettingsFinished.connect(lambda *args: results.append(args))
    first = backend.apply_heater_settings("Julia", 22, "program", 60)
    try:
        assert await asyncio.to_thread(entered.wait, 1)
        await asyncio.wait_for(first, .3)
        assert results[-1][1] is False
        await backend.apply_heater_settings("Juras", 23, "program", 60)
        assert results[-1][1] is False
        assert client.set_mode_program.call_count == 1
        client.set_target_temperature.assert_not_called()
        client.get_devices.assert_not_called()
        release.set()
        async with asyncio.timeout(1):
            while backend._operations.busy(("heater", "shared")):
                await asyncio.sleep(.01)
        client.set_target_temperature.assert_not_called()
    finally:
        release.set()
        await asyncio.gather(first, return_exceptions=True)
        await backend.shutdown()
