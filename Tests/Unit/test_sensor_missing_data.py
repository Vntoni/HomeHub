from unittest.mock import Mock

import pytest

from Adapters.zigbee_sensor_adapter import ZigbeeSensorAdapter
from App.sensor_service import SensorService


@pytest.fixture
def adapter(monkeypatch):
    monkeypatch.setattr("Adapters.zigbee_sensor_adapter.mqtt.Client", Mock())
    monkeypatch.setattr("Adapters.zigbee_sensor_adapter.threading.Thread", Mock())
    return ZigbeeSensorAdapter("test")


@pytest.mark.parametrize("payload", [{}, {"temperature": None, "humidity": 48},
                                      {"temperature": 21.5}, {"humidity": 48},
                                      {"temperature": "bad", "humidity": 48}])
def test_missing_or_invalid_measurements_are_none(adapter, payload):
    adapter._data = payload
    if "temperature" not in payload or payload.get("temperature") is None:
        assert adapter.get_temperature() is None
    if "humidity" not in payload or payload.get("humidity") is None:
        assert adapter.get_humidity() is None
    if payload.get("temperature") == "bad":
        assert adapter.get_temperature() is None


def test_zero_is_a_real_measurement(adapter):
    adapter._data = {"temperature": 0, "humidity": 0, "battery": 0, "linkquality": 0}
    assert adapter.get_temperature() == 0.0
    assert adapter.get_humidity() == 0.0
    assert adapter.get_battery_level() == 0.0
    assert adapter.get_link_quality() == 0


async def test_missing_values_are_not_written_but_zero_is_written(caplog):
    writes = []
    async def save(*args):
        writes.append(args)
    service = SensorService({}, repository=Mock(save_sensor_reading=save))

    service.record_reading("room", {"temperature": 0, "humidity": 0})
    service.record_reading("room", {"temperature": None, "humidity": 48})
    service.record_reading("room", {"temperature": 21.5})
    service.record_reading("room", {"temperature": float("nan"), "humidity": 48})
    await service.aclose()

    assert len(writes) == 1
    assert writes[0][1:3] == (0.0, 0.0)
    assert "Skipping sensor reading" in caplog.text
