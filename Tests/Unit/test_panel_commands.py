"""Commands used by the touch panel; all devices are in-memory fakes."""
import asyncio
from unittest.mock import AsyncMock

import pytest

from Compositions.demo import build_demo_backend
from Ports.washer import WasherSnapshot


async def test_ac_apply_orders_commands_and_reports_readback_failure():
    backend = await build_demo_backend()
    calls, results = [], []
    for name in ("set_operating_mode", "set_target_temp", "set_economy", "set_powerful", "set_low_noise", "refresh"):
        async def record(*args, name=name):
            calls.append(name)
            if name == "refresh":
                raise RuntimeError("offline")
        setattr(backend._climate, name, record)
    backend.acSettingsFinished.connect(lambda *args: results.append(args))
    await backend.apply_ac_settings("Salon", 22.5, "HEAT", False, True, False)
    assert calls == ["set_operating_mode", "set_target_temp", "set_economy", "set_powerful", "set_low_noise", "refresh"]
    assert results[0][:2] == ("Salon", False)


async def test_heater_apply_stops_after_rejected_mode():
    backend = await build_demo_backend()
    backend._heater.set_mode = AsyncMock(side_effect=RuntimeError("rejected"))
    backend._heater.set_target_temp = AsyncMock()
    results = []
    backend.heaterSettingsFinished.connect(lambda *args: results.append(args))
    await backend.apply_heater_settings("Julia", 22.5, "program", 60)
    backend._heater.set_target_temp.assert_not_awaited()
    assert results[0][:2] == ("Julia", False)


async def test_heater_can_be_enabled_after_being_disabled():
    backend = await build_demo_backend()
    states = []
    backend.heaterPowerChanged.connect(lambda room, on: states.append((room, on)))
    await backend.apply_device_power("heater", "Julia", False)
    await backend.apply_device_power("heater", "Julia", True)
    assert [(room, on) for room, on in states if room == "Julia"] == [("Julia", False), ("Julia", True)]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 66.0, 39.5])
async def test_invalid_boiler_temperature_never_reaches_device(value):
    backend = await build_demo_backend()
    backend._boiler.set_mode = AsyncMock()
    results = []
    backend.boilerSettingsFinished.connect(lambda ok, message: results.append(ok))
    await backend.apply_water_heater_settings(value, "GREEN")
    backend._boiler.set_mode.assert_not_awaited()
    assert results == [False]


async def test_settings_reply_identifies_device_and_does_not_broadcast_to_other_forms():
    backend = await build_demo_backend()
    settings, broadcasts = [], []
    backend.deviceSettingsReceived.connect(lambda *args: settings.append(args))
    backend.targetTemperatureReceived.connect(lambda *args: broadcasts.append(args))
    await backend.load_device_settings("ac", "Salon")
    assert settings[0][:2] == ("ac", "Salon")
    assert settings[0][2]["target"] == 22.0
    assert not broadcasts


async def test_commands_for_same_device_do_not_interleave():
    backend = await build_demo_backend()
    calls = []
    async def mode(room, value):
        calls.append("mode")
        await asyncio.sleep(0.01)
    async def temp(room, value, duration):
        calls.append("temp")
    backend._heater.set_mode = mode
    backend._heater.set_target_temp = temp
    await asyncio.gather(
        backend.apply_heater_settings("Julia", 22.0, "program", 60),
        backend.apply_heater_settings("Julia", 23.0, "program", 120))
    assert calls == ["mode", "temp", "mode", "temp"]


async def test_washer_disconnect_clears_previous_countdown():
    backend = await build_demo_backend()
    remaining = []
    backend.washerRemainingChanged.connect(remaining.append)
    backend._on_washer_snapshot(WasherSnapshot(True, 42, None))
    backend._on_washer_snapshot(WasherSnapshot(False, None, None))
    assert remaining == [42, -1]


async def test_ac_off_uses_power_command_not_invalid_mode_enum():
    backend = await build_demo_backend()
    backend._climate.set_operating_mode = AsyncMock()
    await backend.apply_ac_settings("Salon", 22.0, "OFF", False, False, False)
    backend._climate.set_operating_mode.assert_not_awaited()
    assert backend._climate.operating_mode("Salon") == "OFF"


async def test_ac_settings_normalize_enum_flags_for_qml():
    from pyairstage.constants import BooleanDescriptors
    backend = await build_demo_backend()
    backend._climate.units["Salon"].update(
        economy=BooleanDescriptors.OFF, powerful=BooleanDescriptors.ON, low_noise=None)
    values = backend._settings("ac", "Salon")
    assert values["economy"] is False
    assert values["powerful"] is True
    assert values["quiet"] is None
