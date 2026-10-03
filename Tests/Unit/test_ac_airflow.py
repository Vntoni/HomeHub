from unittest.mock import AsyncMock, Mock

import pytest
from pyairstage.airstageAC import AirstageAC
from pyairstage.constants import ACParameter, BooleanProperty, VerticalSwingPositions
from Adapters.airstage_ac_adapter import AirstageACAdapter
from Compositions.demo import build_demo_backend


def adapter(positions=4, swing="0"):
    api = Mock(set_parameter=AsyncMock(return_value=True))
    ac = AirstageACAdapter("test", api, AirstageAC)
    ac._impl.refresh_parameters(data={"parameters": [
        {"name": ACParameter.VERTICAL_SWING_POSITIONS.value, "value": str(positions)},
        {"name": ACParameter.VERTICAL_DIRECTION.value, "value": "1"},
        {"name": ACParameter.VERTICAL_SWING.value, "value": swing},
    ]})
    return ac, api


@pytest.mark.parametrize("count", [4, 6, 8])
async def test_supported_positions_and_swing_use_real_sdk(count):
    ac, api = adapter(count)
    assert len(ac.get_airflow_options()) == count + 1
    assert ac.get_airflow() == "HIGHEST"
    await ac.set_airflow("SWING")
    assert api.set_parameter.await_args.args[1:] == (ACParameter.VERTICAL_SWING, BooleanProperty.ON)
    assert ac.get_airflow() == "SWING"
    await ac.set_airflow("LOWEST")
    assert api.set_parameter.await_args_list[-2].args[1:] == (ACParameter.VERTICAL_SWING, BooleanProperty.OFF)
    assert int(api.set_parameter.await_args.args[2]) == count
    assert ac.get_airflow() == "LOWEST"


async def test_unsupported_position_does_not_write():
    ac, api = adapter(4)
    with pytest.raises(ValueError):
        await ac.set_airflow("CENTER_HIGH")
    api.set_parameter.assert_not_awaited()


def test_missing_capabilities_do_not_break_settings():
    ac, _ = adapter(0)
    assert ac.get_airflow_options() == []
    assert ac.get_airflow() == ""


@pytest.mark.parametrize("value,mode,confirmed,success", [
    ("SWING", "HEAT", True, True), ("LOW", "HEAT", True, True),
    ("SWING", "HEAT", False, False), ("INVALID", "HEAT", True, False),
    ("SWING", "OFF", True, False),
])
async def test_backend_validates_on_capability_and_readback(value, mode, confirmed, success):
    backend = await build_demo_backend()
    backend._climate.units["Salon"]["mode"] = mode
    setter = AsyncMock(wraps=backend._climate.set_airflow if confirmed else None)
    backend._climate.set_airflow = setter
    results = []
    backend.acSettingsFinished.connect(lambda room, ok, message: results.append(ok))
    await backend.apply_ac_settings("Salon", 22, "HEAT", False, False, False, "", value)
    assert results == [success]
    if mode == "OFF" or value == "INVALID":
        setter.assert_not_awaited()
    assert backend._climate.airflow("Jadalnia") == "HIGH"
