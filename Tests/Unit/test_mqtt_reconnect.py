import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from Adapters.zigbee_sensor_adapter import ZigbeeSensorAdapter
from App.sensor_service import SensorService


@pytest.fixture
def sensor(monkeypatch):
    client = Mock()
    monkeypatch.setattr("Adapters.zigbee_sensor_adapter.mqtt.Client", Mock(return_value=client))
    with monkeypatch.context() as scoped:
        scoped.setattr("Adapters.zigbee_sensor_adapter.threading.Thread", Mock())
        adapter = ZigbeeSensorAdapter("test", on_update=Mock())
    return adapter


def test_initial_failures_retry_then_subscribe_and_receive_once(sensor):
    attempts = []
    def connect(*args):
        attempts.append(args)
        if len(attempts) <= 2:
            raise ConnectionRefusedError("broker unavailable")
    sensor._client.connect.side_effect = connect
    def network_loop():
        sensor._on_connect(sensor._client, None, None, 0, None)
        sensor._on_message(sensor._client, None, SimpleNamespace(
            topic=sensor._topic, payload=b'{"temperature": 21}'))
    sensor._client.loop_forever.side_effect = network_loop
    waits = []
    # Controlled waiting: no broker and no actual delay.
    sensor._stop = Mock(is_set=Mock(return_value=False),
                        wait=Mock(side_effect=lambda delay: waits.append(delay) or False))
    sensor._run()
    assert len(attempts) == 3
    assert waits == [1, 2]
    sensor._client.loop_forever.assert_called_once()
    sensor._client.subscribe.assert_called_once_with(sensor._topic)
    sensor._on_update.assert_called_once()
    assert sensor.get_temperature() == 21


def test_backoff_is_capped_and_stop_prevents_more_attempts(sensor):
    sensor._client.connect.side_effect = ConnectionRefusedError
    waits = []
    sensor._stop = Mock(is_set=Mock(return_value=False), wait=Mock(
        side_effect=lambda delay: waits.append(delay) or len(waits) == 9))
    sensor._run()
    assert waits == [1, 2, 4, 8, 16, 32, 60, 60, 60]
    assert sensor._client.connect.call_count == 9
    sensor._client.loop_forever.assert_not_called()


def test_failed_connack_does_not_subscribe_and_disconnect_marks_offline(sensor):
    sensor._on_connect(sensor._client, None, None, 135, None)
    sensor._client.subscribe.assert_not_called()
    assert not sensor.is_online()
    sensor._on_connect(sensor._client, None, None, 0, None)
    assert sensor.is_online()
    sensor._on_disconnect(sensor._client, None, None, 128, None)
    assert not sensor.is_online()
    sensor._on_connect(sensor._client, None, None, 0, None)
    assert sensor.is_online()
    assert sensor._client.subscribe.call_count == 2  # Once for each successful connection.


def test_close_interrupts_real_worker_backoff(sensor):
    attempted = threading.Event()
    def connect(*args):
        attempted.set()
        raise ConnectionRefusedError
    sensor._client.connect.side_effect = connect
    sensor._thread = threading.Thread(target=sensor._run)
    sensor._thread.start()
    try:
        assert attempted.wait(1)
        sensor.close()
        sensor.close()
        assert not sensor._thread.is_alive()
        assert not sensor.is_online()
        sensor._client.loop_forever.assert_not_called()
        assert sensor._client.connect.call_count == 1
    finally:
        if hasattr(sensor, "_stop"):
            sensor._stop.set()
        sensor._thread.join(1)


def test_stop_before_worker_start_does_not_connect(sensor):
    sensor._thread = threading.Thread(target=sensor._run)
    sensor.close()
    sensor._thread.start()
    sensor._thread.join(1)
    sensor._client.connect.assert_not_called()


def test_close_during_connect_does_not_enter_network_loop(sensor):
    connecting = threading.Event()
    release = threading.Event()
    def connect(*args):
        connecting.set()
        assert release.wait(2)
    sensor._client.connect.side_effect = connect
    sensor._client.disconnect.side_effect = release.set
    sensor._thread = threading.Thread(target=sensor._run)
    sensor._thread.start()
    try:
        assert connecting.wait(1)
        sensor.close()
        assert not sensor._thread.is_alive()
        sensor._client.loop_forever.assert_not_called()
    finally:
        release.set()
        sensor._stop.set()
        sensor._thread.join(1)


def test_late_connection_callback_after_close_does_not_subscribe(sensor):
    sensor._stop.set()
    sensor._on_connect(sensor._client, None, None, 0, None)
    sensor._client.subscribe.assert_not_called()
    assert not sensor.is_online()


def test_close_reports_worker_that_does_not_exit(sensor):
    sensor._thread.is_alive.return_value = True
    with pytest.raises(TimeoutError):
        sensor.close()


def test_existing_connection_retries_are_delegated_to_paho_with_bounded_delay(sensor):
    sensor._client.reconnect_delay_set.assert_called_once_with(min_delay=1, max_delay=60)


async def test_service_stops_adapter_outside_event_loop_before_draining_writes():
    owner = threading.get_ident()
    writes = []
    async def save(room, temp, humidity, timestamp):
        writes.append(temp)
    def close():
        assert threading.get_ident() != owner
        # HH-10 requires both measurements for a persisted reading. Missing
        # humidity has its own rejection tests; here we test shutdown draining.
        service.record_reading("room", {"temperature": 20, "humidity": 45})
    service = SensorService({"room": Mock(close=close)}, repository=Mock(save_sensor_reading=save))
    await service.aclose()
    assert writes == [20]


async def test_one_failed_close_does_not_skip_other_sensors_or_accepted_writes(caplog):
    healthy = Mock(close=Mock())
    service = SensorService({"bad": Mock(close=Mock(side_effect=TimeoutError)), "ok": healthy})
    await service.aclose()
    healthy.close.assert_called_once()
    assert "TimeoutError" in caplog.text
