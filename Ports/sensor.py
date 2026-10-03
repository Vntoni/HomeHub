from typing import Protocol
import math


def sensor_measurement(data, key: str) -> float | None:
    """Normalize an optional finite measurement without inventing a zero."""
    value = data.get(key) if isinstance(data, dict) else None
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None

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
