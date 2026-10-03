from unittest.mock import AsyncMock, Mock

import pytest
from pyairstage.airstageAC import AirstageAC
from pyairstage.constants import ACParameter

from Adapters.airstage_ac_adapter import AirstageACAdapter


def payload(power="0"):
    return {"connectionStatus": "Online", "parameters": [
        {"name": ACParameter.ONOFF_MODE.value, "value": power},
        {"name": ACParameter.OPERATION_MODE.value, "value": "4"},
    ]}


async def test_sdk_optimistic_write_does_not_change_confirmed_mode_and_readback_recovers():
    api = Mock(get_devices=AsyncMock(return_value={"test-ac": payload()}),
               set_parameter=AsyncMock(return_value=0))
    adapter = AirstageACAdapter("test-ac", api, AirstageAC)
    await adapter.refresh()
    await adapter.turn_on()
    assert adapter._impl.get_operating_mode().value == "HEAT"
    assert adapter.get_operating_mode() == "OFF"


    api.get_devices.side_effect = ConnectionError("fake read failure")
    with pytest.raises(ConnectionError):
        await adapter.refresh()
    assert adapter.get_operating_mode() == "OFF"
    api.get_devices.side_effect = None
    api.get_devices.return_value = {"test-ac": payload("1")}
    await adapter.refresh()
    assert adapter.get_operating_mode() == "HEAT"
    api.set_parameter.assert_awaited_once()


async def test_incomplete_power_readback_keeps_last_confirmed_on_state():
    api = Mock(get_devices=AsyncMock(return_value={"test-ac": payload("1")}))
    adapter = AirstageACAdapter("test-ac", api, AirstageAC)
    await adapter.refresh()
    api.get_devices.return_value = {"test-ac": {"connectionStatus": "Online", "parameters": []}}
    with pytest.raises(ValueError, match="valid power/mode"):
        await adapter.refresh()
    assert adapter.get_operating_mode() == "HEAT"


async def test_off_write_keeps_confirmed_on_until_readback():
    api = Mock(get_devices=AsyncMock(return_value={"test-ac": payload("1")}),
               set_parameter=AsyncMock(return_value=0))
    adapter = AirstageACAdapter("test-ac", api, AirstageAC)
    await adapter.refresh()
    await adapter.turn_off()
    assert adapter.get_operating_mode() == "HEAT"
    api.get_devices.return_value = {"test-ac": payload("0")}
    await adapter.refresh()
    assert adapter.get_operating_mode() == "OFF"
