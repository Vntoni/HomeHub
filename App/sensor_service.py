from Ports.sensor import SensorPort
from typing import Dict

class SensorService:
    """Service zarządzający wieloma grzejnikami"""

    def __init__(self, sensors: Dict[str, SensorPort]):
        """
        Args:
            sensors: Słownik {nazwa_pokoju: SensorPort}
                    np. {"Salon": sensor_salon, "Sypialnia": sensor_sypialnia}
        """
        self._sensor = sensors


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
