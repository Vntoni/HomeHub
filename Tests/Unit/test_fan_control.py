"""Fan settings: actual pyairstage encoding with a fake cloud transport."""
from unittest.mock import AsyncMock, Mock

import pytest
from pyairstage.airstageAC import AirstageAC
from pyairstage.constants import ACParameter, FanSpeed

from Adapters.airstage_ac_adapter import AirstageACAdapter
from App.climate_service import ClimateService
from Compositions.demo import build_demo_backend


@pytest.mark.parametrize("name,wire_value", [
    ("QUIET", 2), ("LOW", 5), ("MEDIUM", 8), ("HIGH", 11), ("AUTO", 0),
])
async def test_service_adapter_and_library_encode_and_read_each_fan_speed(name, wire_value):
    api = Mock(set_parameter=AsyncMock(return_value=0))
    adapter = AirstageACAdapter("device-salon", api, AirstageAC)
    service = ClimateService({"Salon": adapter})
    await service.set_fan_speed("Salon", name)
    api.set_parameter.assert_awaited_once_with("device-salon", ACParameter.FAN_SPEED, FanSpeed[name])
    sent = api.set_parameter.call_args.args[2]
    assert isinstance(sent, FanSpeed)
    assert int(sent) == wire_value
    assert service.fan_speed("Salon") == name


@pytest.mark.parametrize("raw,expected", [(7, "MEDIUM_LOW"), (9, "MEDIUM_HIGH"), (999, "UNKNOWN"), (None, "UNKNOWN")])
def test_unusual_readbacks_are_not_silently_changed_to_auto(raw, expected):
    adapter = AirstageACAdapter("device-salon", Mock(), AirstageAC)
    adapter._impl._cache[ACParameter.FAN_SPEED] = raw
    assert adapter.get_fan_speed() == expected


async def test_fan_mode_saves_fan_without_temperature_command():
    backend = await build_demo_backend()
    backend._climate.set_target_temp = AsyncMock()
    results, readbacks = [], []
    backend.acSettingsFinished.connect(lambda *args: results.append(args))
    backend.acFanSpeedReceived.connect(lambda *args: readbacks.append(args))
    await backend.apply_ac_settings("Salon", float("nan"), "FAN", False, False, False, "HIGH")
    backend._climate.set_target_temp.assert_not_awaited()
    assert backend._climate.fan_speed("Salon") == "HIGH"
    assert backend._climate.fan_speed("Jadalnia") == "AUTO"
    assert results[0][:2] == ("Salon", True)
    assert readbacks == [("Salon", "HIGH")]


async def test_rejected_fan_write_is_reported_as_failure():
    backend = await build_demo_backend()
    backend._climate.set_fan_speed = AsyncMock(side_effect=RuntimeError("cloud rejected write"))
    backend._climate.turn_on = AsyncMock()
    results = []
    backend.acSettingsFinished.connect(lambda *args: results.append(args))
    await backend.apply_ac_settings("Salon", 22.0, "HEAT", False, False, False, "QUIET")
    assert results[0][:2] == ("Salon", False)
    backend._climate.turn_on.assert_not_awaited()


@pytest.mark.parametrize("fan_speed", ["invalid", "MEDIUM_LOW", "2"])
async def test_invalid_fan_speed_fails_before_any_device_write(fan_speed):
    backend = await build_demo_backend()
    backend._climate.set_operating_mode = AsyncMock()
    results = []
    backend.acSettingsFinished.connect(lambda *args: results.append(args))
    await backend.apply_ac_settings("Salon", 22.0, "HEAT", False, False, False, fan_speed)
    backend._climate.set_operating_mode.assert_not_awaited()
    assert results[0][:2] == ("Salon", False)


async def test_untouched_intermediate_fan_reading_is_preserved():
    backend = await build_demo_backend()
    backend._climate.units["Salon"]["fan_speed"] = "MEDIUM_LOW"
    backend._climate.set_fan_speed = AsyncMock()
    assert backend._settings("ac", "Salon")["fan_speed"] == "MEDIUM_LOW"
    await backend.apply_ac_settings("Salon", 22.0, "HEAT", False, False, False, "")
    backend._climate.set_fan_speed.assert_not_awaited()
    assert backend._climate.fan_speed("Salon") == "MEDIUM_LOW"


async def test_off_does_not_send_fan_command():
    backend = await build_demo_backend()
    backend._climate.set_fan_speed = AsyncMock()
    await backend.apply_ac_settings("Salon", 22.0, "OFF", False, False, False, "LOW")
    backend._climate.set_fan_speed.assert_not_awaited()
    assert backend._climate.operating_mode("Salon") == "OFF"
