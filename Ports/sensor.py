from typing import Protocol

class SensorPort(Protocol):
    """Port dla elektrycznego grzejnika (Cozy Touch)"""


    def get_data(self) -> dict:
        """Pobierz aktualne dane z czujnika"""
        ...

    def get_battery_level(self) -> float | None:
        """Pobierz status baterii"""
        ...

    def get_temperature(self) -> float | None:
        """Pobierz aktualną temperaturę"""
        ...

    def get_humidity(self) -> float | None:
        """Pobierz aktualną wilgotność"""
        ...

    def get_link_quality(self) -> int | None:
        """Pobierz moc sygnału"""
        ...
