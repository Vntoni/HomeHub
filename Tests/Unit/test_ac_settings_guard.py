from unittest.mock import AsyncMock

import pytest

from Compositions.demo import build_demo_backend


@pytest.mark.parametrize("readback", ["OFF", "UNKNOWN", None, "failure"])
async def test_fresh_readback_must_confirm_on_before_any_settings_write(readback):
    backend = await build_demo_backend()
    results = []
    backend.acSettingsFinished.connect(lambda *args: results.append(args))
    # The form and backend cache still say HEAT when the external state changes.
    assert backend._climate.operating_mode("Salon") == "HEAT"
    async def refresh(room):
        if readback == "failure":
            raise ConnectionError("unavailable")
        backend._climate.units[room]["mode"] = readback
    backend._climate.refresh = refresh
    writes = ["set_operating_mode", "set_target_temp", "set_fan_speed",
              "set_economy", "set_powerful", "set_low_noise", "turn_on", "turn_off"]
    for name in writes:
        setattr(backend._climate, name, AsyncMock())
    await backend.apply_ac_settings("Salon", 22, "HEAT", False, False, False, "AUTO")
    for name in writes:
        getattr(backend._climate, name).assert_not_awaited()
    assert results[-1][:2] == ("Salon", False)
    assert backend._climate.operating_mode("Jadalnia") == "HEAT"


@pytest.mark.parametrize("cached", ["OFF", "UNKNOWN", None])
async def test_unconfirmed_cached_power_cannot_authorize_settings(cached):
    backend = await build_demo_backend()
    backend._climate.units["Salon"]["mode"] = cached
    backend._climate.set_operating_mode = AsyncMock()
    await backend.apply_ac_settings("Salon", 22, "HEAT", False, False, False)
    backend._climate.set_operating_mode.assert_not_awaited()
