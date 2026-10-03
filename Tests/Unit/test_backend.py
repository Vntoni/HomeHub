import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from PySide6.QtCore import QCoreApplication

from App.sensor_service import SensorService
from Interface.qt_backend import QtHomeBackend


@pytest.fixture(scope="session")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture
def backend(qt_app):
    climate = Mock(refresh_all=AsyncMock(), online_map=Mock(return_value={}))
    boiler = Mock(refresh=AsyncMock(), set_mode=AsyncMock(), set_target_temp=AsyncMock(),
                  get_target_temp=Mock(return_value=55.0), get_mode=Mock(return_value="GREEN"),
                  get_current_temp=Mock(return_value=43.0), get_power=Mock(return_value=True))
    return QtHomeBackend(climate, boiler, None)


async def test_failed_refresh_reports_boiler_offline(backend):
    backend._boiler.refresh.side_effect = RuntimeError("offline")
    received = []
    stale = []
    backend.boilerOnlineChanged.connect(received.append)
    backend.deviceStaleChanged.connect(lambda *args: stale.append(args))
    await backend.init_all()
    assert received == [False]
    assert ("boiler", "boiler", True) in stale


async def test_successful_refresh_clears_boiler_stale_state(backend):
    backend._device_stale[("boiler", "boiler")] = True
    stale = []
    backend.deviceStaleChanged.connect(lambda *args: stale.append(args))
    await backend.init_all()
    assert ("boiler", "boiler", False) in stale


async def test_settings_are_sequential_and_emit_refreshed_state(backend):
    calls = []
    for name in ("set_mode", "set_target_temp", "refresh"):
        async def record(*args, name=name):
            calls.append((name, args))
        getattr(backend._boiler, name).side_effect = record
    temperatures, results = [], []
    backend.targetTemperatureReceived.connect(lambda *args: temperatures.append(args))
    backend.boilerSettingsFinished.connect(lambda *args: results.append(args))
    await backend.apply_water_heater_settings(55.0, "GREEN")
    assert calls == [("set_mode", ("GREEN",)), ("set_target_temp", (55.0,)), ("refresh", ())]
    assert temperatures == [("boiler", 55.0)]
    assert results[0][0] is True


@pytest.mark.parametrize("failure", ["set_mode", "set_target_temp", "refresh"])
async def test_partial_or_failed_settings_never_report_success(backend, failure):
    getattr(backend._boiler, failure).side_effect = RuntimeError("failure")
    results = []
    backend.boilerSettingsFinished.connect(lambda ok, message: results.append(ok))
    await backend.apply_water_heater_settings(55.0, "GREEN")
    assert results == [False]


async def test_sensor_refresh_uses_configured_room_keys(backend):
    backend._sensors = SensorService({"sypialnia": Mock(
        get_temperature=Mock(return_value=21.5), get_humidity=Mock(return_value=48.0))})
    values = []
    backend.sensorTempChanged.connect(lambda *args: values.append(args))
    await backend.init_all()
    assert values == [("sypialnia", 21.5)]


async def test_mode_slot_accepts_qml_string(backend):
    await backend.set_water_heater_mode("BOOST")
    backend._boiler.set_mode.assert_awaited_once_with("BOOST")
    assert backend.metaObject().indexOfMethod("set_water_heater_mode(QString)") >= 0


async def test_shutdown_cancels_registered_task_and_closes_resource(backend):
    closed = []
    class Resource:
        async def close(self):
            closed.append("resource")
    task = asyncio.create_task(asyncio.sleep(60))
    backend.register_task(task)
    backend.register_resource(Resource())
    await backend.shutdown()
    assert task.cancelled()
    assert closed == ["resource"]
    await backend.shutdown()


async def test_shutdown_drains_sensors_before_database_and_reports_close_errors(backend):
    events = []
    class Sensors:
        async def aclose(self):
            events.append("sensor-final-write")
    class Database:
        async def close(self):
            events.append("database")
    class BrokenResource:
        async def close(self):
            events.append("broken")
            raise RuntimeError("close failed")
    backend._sensors = Sensors()
    backend.register_resource(Database())
    backend.register_resource(BrokenResource())
    with pytest.raises(ExceptionGroup):
        await backend.shutdown()
    assert events == ["sensor-final-write", "broken", "database"]
