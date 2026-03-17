from typing import Protocol
from datetime import datetime


class ReadingRepositoryPort(Protocol):
    """Port dla persystencji odczytów (czujniki, pogoda, zużycie prądu)."""

    async def save_sensor_reading(
        self, room: str, temperature: float, humidity: float, ts: datetime
    ) -> None:
        """Zapisz odczyt z czujnika wewnętrznego."""
        ...

    async def save_weather_reading(
        self,
        temp_out: float,
        humidity_out: float,
        condition: str,
        wind_speed: float,
        ts: datetime,
    ) -> None:
        """Zapisz odczyt pogody zewnętrznej."""
        ...

    async def save_power_reading(
        self, device: str, watt_h: float, ts: datetime
    ) -> None:
        """Zapisz odczyt zużycia prądu (Shelly EM – przyszłość)."""
        ...

    async def get_sensor_history(
        self, room: str, since: datetime, until: datetime | None = None
    ) -> list[dict]:
        """Pobierz historię odczytów czujnika dla pokoju."""
        ...

    async def get_weather_history(
        self, since: datetime, until: datetime | None = None
    ) -> list[dict]:
        """Pobierz historię pogody zewnętrznej."""
        ...

    async def get_latest_sensor_reading(self, room: str) -> dict | None:
        """Pobierz ostatni odczyt z czujnika dla pokoju."""
        ...

    async def get_latest_weather_reading(self) -> dict | None:
        """Pobierz ostatni odczyt pogody."""
        ...

