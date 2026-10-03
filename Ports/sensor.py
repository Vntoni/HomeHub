from typing import Protocol
import math


def configured_sensor_rooms(value: str) -> list[str]:
    """Keep configured sensors and include the installed bathroom sensor.

    Older deployed .env files list only salon,jadalnia. The temperature map
    also uses czujnik_lazienka; include it without rewriting user credentials.
    """
    return list(dict.fromkeys([room.strip() for room in value.split(",") if room.strip()] + ["lazienka"]))


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
