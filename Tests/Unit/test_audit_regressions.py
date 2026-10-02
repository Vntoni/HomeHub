"""Acceptance tests for audited defects. Failures remain visible until phase 4."""
import asyncio
from copy import deepcopy
from unittest.mock import AsyncMock, Mock

import httpx
from pyairstage.airstageAC import AirstageAC
from pyairstage.constants import ACParameter, OperationMode
from PySide6.QtCore import QCoreApplication

from Adapters.airstage_ac_adapter import AirstageACAdapter
from Adapters.open_meteo_adapter import OpenMeteoAdapter
from App.climate_service import ClimateService
from App.sensor_service import SensorService
from Compositions.demo import build_demo_backend


def device_payload():
    return {"connectionStatus": "Online", "parameters": [
        {"name": ACParameter.ONOFF_MODE.value, "value": "0"},
        {"name": ACParameter.OPERATION_MODE.value, "value": str(int(OperationMode.HEAT))},
        {"name": ACParameter.INDOOR_TEMPERATURE.value, "value": "7150"},
        {"name": ACParameter.TARGET_TEMPERATURE.value, "value": "220"},
    ]}


async def test_hh01_failed_readback_does_not_publish_optimistic_power():
    app = QCoreApplication.instance() or QCoreApplication([])
    backend = await build_demo_backend()
    physical_state = device_payload()
    api = Mock(set_parameter=AsyncMock(return_value=0))
    adapter = AirstageACAdapter("test-ac", api, AirstageAC)
    adapter._impl.refresh_parameters(deepcopy(physical_state))
    # Isolate HH-01 from HH-02: refresh fails after an accepted write.
    adapter.refresh = AsyncMock(side_effect=ConnectionError("fake readback failure"))
    backend._climate = ClimateService({"Salon": adapter})
    readings, results = [], []
    backend.modeReceived.connect(lambda room, mode: readings.append((room, mode)))
    backend.devicePowerFinished.connect(lambda *args: results.append(args))
    try:
        await backend.publish_dashboard()
        assert readings[-1] == ("Salon", "OFF")
        await backend.apply_device_power("ac", "Salon", True)
        await backend.publish_dashboard()
        api.set_parameter.assert_awaited_once()
        assert results[-1][2] is False
        assert physical_state["parameters"][0]["value"] == "0"
        assert all(mode != "HEAT" for room, mode in readings), readings
    finally:
        await backend.shutdown()


async def test_hh02_adapter_refresh_matches_installed_sdk_contract():
    api = Mock(get_devices=AsyncMock(return_value={"test-ac": device_payload()}))
    adapter = AirstageACAdapter("test-ac", api, AirstageAC)
    await adapter.refresh()
    api.get_devices.assert_awaited_once()
    assert adapter.is_online()
    assert adapter.get_operating_mode() == "OFF"


async def test_hh03_mqtt_thread_persists_exactly_one_reading():
    writes = []
    written = asyncio.Event()
    async def save(*args):
        writes.append(args)
        written.set()
    service = SensorService({}, repository=Mock(save_sensor_reading=save))
    await asyncio.to_thread(service.record_reading, "test-room",
                            {"temperature": 21.5, "humidity": 48.0})
    await asyncio.wait_for(written.wait(), timeout=0.5)
    assert len(writes) == 1
    assert writes[0][:3] == ("test-room", 21.5, 48.0)


async def test_hh04_weather_maps_successful_fake_http_response(monkeypatch):
    calls = []
    async def response(client, url, **kwargs):
        calls.append(url)
        return httpx.Response(200, request=httpx.Request("GET", url), json={"current": {
            "temperature_2m": 12.5, "relative_humidity_2m": 65,
            "wind_speed_10m": 3.0, "weather_code": 0,
        }})
    # Do not inject the missing module into application globals: that hides HH-04.
    monkeypatch.setattr(httpx.AsyncClient, "get", response)
    reading = await OpenMeteoAdapter(0, 0).fetch()
    assert reading is not None, "HH-04: valid fake response must produce a reading"
    assert calls
    assert (reading["temp_out"], reading["humidity_out"], reading["wind_speed"]) == (12.5, 65, 3.0)
