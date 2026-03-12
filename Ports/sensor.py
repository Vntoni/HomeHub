from typing import Protocol

class SensorPort(Protocol):
    """Port dla elektrycznego grzejnika (Cozy Touch)"""


    def get_data(self) -> dict:
        """Pobierz aktualne dane z czujnika"""
        ...

    def get_battery_level(self) -> float:
        """Pobierz status baterii"""
        ...

    def get_temperature(self) -> float:
        """Pobierz aktualną temperaturę"""
        ...

    def get_humidity(self) -> float:
        """Pobierz aktualną wilgotność"""
        ...

    def get_link_quality(self) -> int:
        """Pobierz moc sygnału"""
        ...
