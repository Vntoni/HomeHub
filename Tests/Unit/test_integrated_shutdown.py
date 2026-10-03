import asyncio
from unittest.mock import Mock

from App.sensor_service import SensorService
from Compositions.demo import build_demo_backend


async def test_last_mqtt_callback_is_persisted_before_database_closes():
    events = []
    saving, release = asyncio.Event(), asyncio.Event()
    class Repository:
        async def save_sensor_reading(self, room, temp, humidity, ts):
            assert (room, temp, humidity) == ("test", 20, 45)
            saving.set()
            await release.wait()
            events.append("saved")
        async def close(self):
            assert events == ["saved"]
            events.append("database-closed")
    repository = Repository()
    def stop_sensor():
        service.record_reading("test", {"temperature": 20, "humidity": 45})
    service = SensorService({"test": Mock(close=stop_sensor)}, repository)
    backend = await build_demo_backend()
    backend._sensors = service
    backend.register_resource(repository)
    shutdown = asyncio.create_task(backend.shutdown())
    try:
        await asyncio.wait_for(saving.wait(), 1)
        assert not shutdown.done()
        assert events == []
        release.set()
        await asyncio.wait_for(shutdown, 2)
        assert events == ["saved", "database-closed"]
        await backend.shutdown()
        assert events == ["saved", "database-closed"]
    finally:
        release.set()
        await shutdown
