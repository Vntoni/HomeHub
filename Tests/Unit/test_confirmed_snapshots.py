from copy import deepcopy
from unittest.mock import AsyncMock, Mock

import pytest

from Adapters.ariston_boiler_adapter import AristonBoilerAdapter
from Adapters.cozytouch_heater_adapter import CozyTouchHeaterAdapter


async def test_boiler_partial_update_retains_complete_snapshot_and_recovers():
    client = Mock(async_update_state=AsyncMock(), async_update_energy=AsyncMock(),
                  water_heater_power_value=True, water_heater_target_temperature=55,
                  water_heater_current_temperature=43, water_heater_current_mode_text="GREEN")
    adapter = AristonBoilerAdapter(client)
    await adapter.refresh()
    client.water_heater_target_temperature = 60
    client.water_heater_power_value = False
    client.async_update_energy.side_effect = ConnectionError("503")
    with pytest.raises(ConnectionError):
        await adapter.refresh()
    assert adapter.get_target_temperature() == 55
    assert adapter.get_power() is True
    client.async_update_energy.side_effect = None
    await adapter.refresh()
    assert adapter.get_target_temperature() == 60
    assert adapter.get_power() is False


@pytest.mark.parametrize("bad", [[], [{"deviceId": 1, "capabilities": []}]])
async def test_heater_failed_or_incomplete_read_retains_snapshot(bad):
    good = [{"deviceId": 1, "capabilities": [
        {"capabilityId": 40, "value": "22"},
        {"capabilityId": 117, "value": "20"},
        {"capabilityId": 184, "value": "1"},
        {"capabilityId": 157, "value": "0"},
    ]}]
    client = Mock(devices=deepcopy(good), get_devices=Mock(return_value=deepcopy(good)))
    adapter = CozyTouchHeaterAdapter(client, 1)
    await adapter.refresh()
    client.devices = bad
    client.get_devices.return_value = bad
    with pytest.raises(ValueError):
        await adapter.refresh()
    assert adapter.get_target_temperature() == 22
    assert adapter.get_current_temperature() == 20
    assert adapter.get_mode() == "program"
    assert adapter.get_power() is False
    good[0]["capabilities"][0]["value"] = "24"
    client.get_devices.return_value = good
    await adapter.refresh()
    assert adapter.get_target_temperature() == 24
