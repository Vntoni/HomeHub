from Ports.sensor import SensorPort
from typing import Dict
from datetime import datetime, timezone
import asyncio
import logging
import threading

logger = logging.getLogger(__name__)


class SensorService:
    """Service zarządzający wieloma czujnikami."""

    def __init__(self, sensors: Dict[str, SensorPort], repository=None):
        """
        Args:
            sensors:    Słownik {nazwa_pokoju: SensorPort}
                        np. {"Salon": sensor_salon, "Sypialnia": sensor_sypialnia}
            repository: Opcjonalny ReadingRepositoryPort – jeśli podany,
                        każdy odczyt jest zapisywany do bazy danych.
        """
        self._sensor = sensors
        self._repo = repository
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None
        self._pending = set()
        self._guard = threading.Lock()
        self._closed = False

    def record_reading(self, room: str, data: dict) -> None:
        """
        Callback wywoływany przez adapter Zigbee przy każdej nowej wiadomości MQTT.
        Jeśli skonfigurowane repozytorium, zapisuje odczyt asynchronicznie.
        """
        if not self._repo:
            return
        temp = float(data.get("temperature", 0.0))
        hum = float(data.get("humidity", 0.0))
        ts = datetime.now(tz=timezone.utc)

        # Capture the owner loop during construction, never in the MQTT thread.
        with self._guard:
            if self._closed or self._loop is None or not self._loop.is_running():
                logger.error("Sensor persistence is not accepting readings")
                return
            coroutine = self._save_reading(room, temp, hum, ts)
            try:
                future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
            except RuntimeError:
                coroutine.close()
                logger.error("Sensor persistence is not accepting readings")
                return
            self._pending.add(future)
        future.add_done_callback(self._write_finished)

    async def _save_reading(self, room, temp, humidity, timestamp):
        await self._repo.save_sensor_reading(room, temp, humidity, timestamp)

    def _write_finished(self, future):
        with self._guard:
            self._pending.discard(future)
        if future.cancelled():
            logger.error("Sensor reading write was cancelled")
        elif future.exception() is not None:
            # Avoid logging exception text containing DSNs or credentials.
            logger.error("Failed to persist sensor reading (%s)",
                         type(future.exception()).__name__)

    async def aclose(self):
        """Stop producers, then give accepted writes up to five seconds."""
        with self._guard:
            closed = self._closed
        if not closed:
            # MQTT close joins a thread. Keep the owner loop available so final
            # callbacks can still schedule and finish their repository writes.
            closers = [asyncio.to_thread(sensor.close) for sensor in self._sensor.values()
                       if callable(getattr(sensor, "close", None))]
            results = await asyncio.gather(*closers, return_exceptions=True)
            for result in results:
                if isinstance(result, BaseException):
                    logger.error("Sensor shutdown failed (%s)", type(result).__name__)
        with self._guard:
            self._closed = True
            pending = tuple(self._pending)
        if pending:
            writes = asyncio.gather(*(asyncio.wrap_future(f) for f in pending),
                                    return_exceptions=True)
            try:
                await asyncio.wait_for(writes, timeout=5)
            except TimeoutError:
                logger.error("Sensor persistence shutdown timed out; pending writes cancelled")


    def rooms(self):
        return tuple(self._sensor)

    async def close(self):
        """Stop adapter-owned MQTT resources during application shutdown."""
        for sensor in self._sensor.values():
            close = getattr(sensor, "close", None)
            if close:
                result = await asyncio.to_thread(close)
                if asyncio.iscoroutine(result):
                    await result

    def get_data(self, room: str) -> dict:
        """Pobierz aktualne dane z czujnika"""
        return self._sensor[room].get_data()


    def get_temperature(self, room: str) -> float:
        """Pobierz aktualna temperaturę"""
        return self._sensor[room].get_temperature()

    def get_humidity(self, room: str) -> float:
        """Pobierz aktualna wilgotność"""
        return self._sensor[room].get_humidity()

    def get_link_quality(self, room: str) -> float:
        """Pobierz moc sygnału"""
        return self._sensor[room].get_link_quality()

    def get_baterry_level(self, room: str) -> float:
        """Pobierz status baterii"""
        return self._sensor[room].get_battery_level()
