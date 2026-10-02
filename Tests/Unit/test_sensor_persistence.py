import asyncio
import logging
from unittest.mock import Mock

import pytest

from App.sensor_service import SensorService


async def test_mqtt_thread_saves_once_on_owner_loop():
    loop = asyncio.get_running_loop()
    writes = asyncio.Queue()
    async def save(*args):
        assert asyncio.get_running_loop() is loop
        writes.put_nowait(args)
    service = SensorService({}, repository=Mock(save_sensor_reading=save))
    await asyncio.to_thread(service.record_reading, "test-room", {"temperature": 21.5, "humidity": 48})
    result = await asyncio.wait_for(writes.get(), timeout=0.5)
    assert result[:3] == ("test-room", 21.5, 48.0)
    assert result[3].tzinfo is not None
    assert writes.empty()


async def test_repository_failure_is_reported(caplog):
    failed = asyncio.Event()
    async def save(*args):
        failed.set()
        raise ConnectionError("fake database unavailable")
    service = SensorService({}, repository=Mock(save_sensor_reading=save))
    with caplog.at_level(logging.ERROR):
        await asyncio.to_thread(service.record_reading, "test-room", {"temperature": 21, "humidity": 48})
        await asyncio.wait_for(failed.wait(), timeout=0.5)
        await service.aclose()
    assert "Failed to persist sensor reading" in caplog.text


async def test_close_drains_accepted_writes_and_rejects_new_readings(caplog):
    values = []
    async def save(room, temp, humidity, timestamp):
        values.append(temp)
    service = SensorService({}, repository=Mock(save_sensor_reading=save))
    def send():
        for value in range(10):
            service.record_reading("test-room", {"temperature": value, "humidity": 48})
    await asyncio.to_thread(send)
    await service.aclose()
    await service.aclose()
    service.record_reading("test-room", {"temperature": 99, "humidity": 48})
    assert values == list(range(10))
    assert "not accepting readings" in caplog.text


def test_closed_owner_loop_is_reported_without_scheduling(caplog):
    loop = asyncio.new_event_loop()
    async def construct():
        return SensorService({}, repository=Mock())
    service = loop.run_until_complete(construct())
    loop.close()
    service.record_reading("test-room", {"temperature": 21, "humidity": 48})
    assert "not accepting readings" in caplog.text


def test_service_constructed_without_owner_loop_fails_explicitly(caplog):
    service = SensorService({}, repository=Mock())
    service.record_reading("test-room", {"temperature": 21, "humidity": 48})
    assert "not accepting readings" in caplog.text
