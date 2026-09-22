from unittest.mock import AsyncMock, Mock
import threading

import pytest

from Adapters.ariston_boiler_adapter import AristonBoilerAdapter
from Adapters.cozytouch_heater_adapter import CozyTouchHeaterAdapter


async def test_boiler_forwards_mode_name_to_ariston():
    client = Mock(async_set_water_heater_operation_mode=AsyncMock())
    await AristonBoilerAdapter(client).set_operation_mode("GREEN")
    client.async_set_water_heater_operation_mode.assert_awaited_once_with("GREEN")


@pytest.mark.parametrize("method,args", [
    ("set_target_temperature", (22.0,)), ("set_power", (True,)),
    ("set_power", (False,)), ("set_mode", ("manual",)), ("set_mode", ("program",)),
])
async def test_heater_rejected_commands_raise(method, args):
    client = Mock()
    for name in ("set_target_temperature", "cancel_exception_mode", "set_mode_manual", "set_mode_program"):
        getattr(client, name).return_value = False
    adapter = CozyTouchHeaterAdapter(client, 123)
    with pytest.raises(RuntimeError, match="did not accept"):
        await getattr(adapter, method)(*args)


async def test_heater_network_command_runs_outside_ui_thread():
    main_thread = threading.get_ident()
    threads = []
    def set_temp(*args):
        threads.append(threading.get_ident())
        return True
    adapter = CozyTouchHeaterAdapter(Mock(set_target_temperature=set_temp), 123)
    await adapter.set_target_temperature(22.0)
    assert threads and threads[0] != main_thread
