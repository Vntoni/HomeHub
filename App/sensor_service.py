from Ports.sensor import SensorPort
from typing import Dict
from datetime import datetime, timezone
import asyncio


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

        # Uruchom zapis jako task w event loop bez blokowania wątku MQTT
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(
                self._repo.save_sensor_reading(room, temp, hum, ts)
            )
        except RuntimeError:
            # Brak event loop w wątku MQTT – pomijamy zapis (nie crashujemy)
            pass


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
