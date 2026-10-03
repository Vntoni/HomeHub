from copy import deepcopy
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


async def test_refresh_awaits_cloud_and_selects_correct_device_without_mutating_response():
    devices = {"first": payload("0"), "second": payload("1")}
    original = deepcopy(devices)
    api = Mock(get_devices=AsyncMock(return_value=devices))
    first = AirstageACAdapter("first", api, AirstageAC)
    second = AirstageACAdapter("second", api, AirstageAC)
    await first.refresh()
    await second.refresh()
    assert first.get_operating_mode() == "OFF"
    assert second.get_operating_mode() == "HEAT"
    assert first.is_online() and second.is_online()
    assert api.get_devices.await_count == 2
    assert devices == original


@pytest.mark.parametrize("bad", [{}, {"first": {}}, {"first": {"parameters": None}},
                                  {"first": {"parameters": [{}]}}])
async def test_bad_payload_preserves_previous_sdk_cache(bad):
    api = Mock(get_devices=AsyncMock(side_effect=[{"first": payload()}, bad]))
    adapter = AirstageACAdapter("first", api, AirstageAC)
    await adapter.refresh()
    before = deepcopy(adapter._impl.get_cache())
    with pytest.raises(ValueError):
        await adapter.refresh()
    assert adapter._impl.get_cache() == before


async def test_timeout_is_propagated_and_next_refresh_recovers():
    api = Mock(get_devices=AsyncMock(side_effect=[TimeoutError(), {"first": payload()}]))
    adapter = AirstageACAdapter("first", api, AirstageAC)
    with pytest.raises(TimeoutError):
        await adapter.refresh()
    await adapter.refresh()
    assert adapter.get_operating_mode() == "OFF"


async def test_legacy_async_refresh_contract_is_preserved():
    implementation = Mock(refresh_parameters=AsyncMock(),
                          get_operating_mode=Mock(return_value=Mock(value="OFF")))
    adapter = AirstageACAdapter("first", Mock(), Mock(return_value=implementation))
    await adapter.refresh()
    implementation.refresh_parameters.assert_awaited_once_with()
