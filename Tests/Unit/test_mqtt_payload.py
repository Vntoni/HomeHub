import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from Adapters.zigbee_sensor_adapter import ZigbeeSensorAdapter


@pytest.fixture
def sensor(monkeypatch):
    # No MQTT connection or background thread is started.
    monkeypatch.setattr("Adapters.zigbee_sensor_adapter.mqtt.Client", Mock())
    monkeypatch.setattr("Adapters.zigbee_sensor_adapter.threading.Thread", Mock())
    return ZigbeeSensorAdapter("test", on_update=Mock())


def deliver(sensor, payload, topic=None):
    sensor._on_message(None, None, SimpleNamespace(
        topic=topic or sensor._topic, payload=payload))


@pytest.mark.parametrize("payload", [
    b"[]", b"null", b'"text"', b"42", b"{", b"\xff",
    b'{"temperature": null}', b'{"temperature": "oops"}',
    b'{"temperature": NaN}', b'{"humidity": Infinity}',
    b'{"battery": -Infinity}', b'{"linkquality": "oops"}',
    b'{"temperature": true}', b'{"humidity": []}',
    b'{"battery": {}}', b'{"linkquality": "1.5"}',
    b'{"linkquality": 1e309}',
])
def test_invalid_message_preserves_valid_cache_and_next_message_works(sensor, payload):
    original = {"temperature": 21.5, "humidity": 48, "battery": 90, "linkquality": 120}
    deliver(sensor, json.dumps(original).encode())
    sensor._on_update.reset_mock()
    deliver(sensor, payload)
    assert sensor.get_data() == original
    sensor._on_update.assert_not_called()
    assert sensor.get_temperature() == 21.5
    assert sensor.get_humidity() == 48
    assert sensor.get_battery_level() == 90
    assert sensor.get_link_quality() == 120
    deliver(sensor, b'{"temperature": 22, "humidity": 49}')
    assert sensor.get_temperature() == 22
    sensor._on_update.assert_called_once()


@pytest.mark.parametrize("data", [
    {}, {"battery": 50}, {"temperature": 0, "humidity": 0},
    {"temperature": "21.5", "humidity": "48", "linkquality": "100"},
    {"temperature": -25, "voltage": 3000, "custom": "value"},
])
def test_valid_partial_and_numeric_string_payloads_keep_existing_contract(sensor, data):
    deliver(sensor, json.dumps(data).encode())
    assert sensor.get_data() == data
    sensor._on_update.assert_called_once_with(sensor._name, data)


def test_callback_failure_does_not_escape_or_prevent_next_message(sensor, caplog):
    sensor._on_update.side_effect = [RuntimeError("private data"), None]
    deliver(sensor, b'{"temperature": 21}')
    deliver(sensor, b'{"temperature": 22}')
    assert sensor._on_update.call_count == 2
    assert sensor.get_temperature() == 22
    assert "RuntimeError" in caplog.text
    assert "private data" not in caplog.text


def test_other_topic_does_not_touch_cache(sensor):
    deliver(sensor, b'[]', topic="zigbee2mqtt/other")
    assert sensor.get_data() == {}
    sensor._on_update.assert_not_called()


def test_installed_bathroom_sensor_is_subscribed_with_legacy_configuration(monkeypatch):
    from Ports.sensor import configured_sensor_rooms
    monkeypatch.setattr("Adapters.zigbee_sensor_adapter.mqtt.Client", Mock())
    monkeypatch.setattr("Adapters.zigbee_sensor_adapter.threading.Thread", Mock())
    assert configured_sensor_rooms("salon,jadalnia") == ["salon", "jadalnia", "lazienka"]
    assert configured_sensor_rooms("lazienka,lazienka") == ["lazienka"]
    sensor = ZigbeeSensorAdapter("lazienka", on_update=Mock())
    sensor._on_connect(sensor._client, None, None, 0, None)
    sensor._client.subscribe.assert_called_once_with("zigbee2mqtt/czujnik_lazienka")
    deliver(sensor, b'{"battery":100,"humidity":65,"linkquality":108,"temperature":20.6,"update":{"state":"idle"}}',
            topic="zigbee2mqtt/czujnik_lazienka")
    assert sensor.get_temperature() == 20.6
    assert sensor.get_humidity() == 65
