"""Open-Meteo HTTP adapter and polling; one implementation and one client."""
import asyncio
from datetime import datetime, timezone

import httpx

# Kody WMO → czytelny opis pogody (PL)
_WMO_CODES: dict[int, str] = {
    0:  "bezchmurnie",
    1:  "przeważnie bezchmurnie", 2: "częściowe zachmurzenie", 3: "pochmurno",
    45: "mgła", 48: "mgła z szronem",
    51: "mżawka lekka", 53: "mżawka", 55: "mżawka gęsta",
    61: "deszcz lekki", 63: "deszcz", 65: "deszcz intensywny",
    71: "śnieg lekki", 73: "śnieg", 75: "śnieg intensywny",
    77: "ziarna śniegu",
    80: "przelotny deszcz lekki", 81: "przelotny deszcz", 82: "przelotny deszcz intensywny",
    85: "przelotny śnieg", 86: "przelotny śnieg intensywny",
    95: "burza", 96: "burza z gradem", 99: "burza z silnym gradem",
}


class OpenMeteoAdapter:
    """
    Pobiera pogodę z Open-Meteo i zapisuje do repozytorium.
    Uruchamiaj przez start_polling() jako asyncio task.
    """

    API_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(
        self,
        latitude: float,
        longitude: float,
        repository=None,
        poll_interval_seconds: int = 600,
    ):
        self._lat = latitude
        self._lon = longitude
        self._repo = repository
        self._interval = poll_interval_seconds
        self._latest: dict | None = None

    async def fetch(self) -> dict | None:
        """Pobierz aktualną pogodę. Zwraca słownik lub None przy błędzie."""
        params = {
            "latitude": self._lat,
            "longitude": self._lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
            "wind_speed_unit": "ms",
            "timezone": "Europe/Warsaw",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(self.API_URL, params=params)
                r.raise_for_status()
                data = r.json()["current"]
                return {
                    "temp_out": data["temperature_2m"],
                    "humidity_out": data["relative_humidity_2m"],
                    "wind_speed": data["wind_speed_10m"],
                    "condition": _WMO_CODES.get(data["weather_code"], "nieznane"),
                    "ts": datetime.now(tz=timezone.utc),
                }
        except Exception as e:
            print(f"[OpenMeteo] Błąd pobierania pogody: {e}")
            return None

    def get_latest(self) -> dict | None:
        """Zwraca ostatnio pobrany odczyt (bez sieci)."""
        return self._latest

    async def start_polling(self) -> None:
        """
        Nieskończona pętla: pobieraj pogodę co `poll_interval_seconds`.
        Uruchom jako: asyncio.create_task(adapter.start_polling())
        """
        print(f"[OpenMeteo] Start pollingu co {self._interval}s (lat={self._lat}, lon={self._lon})")
        while True:
            weather = await self.fetch()
            if weather:
                self._latest = weather
                print(
                    f"[OpenMeteo] {weather['temp_out']}°C, "
                    f"{weather['humidity_out']}% RH, "
                    f"{weather['wind_speed']} m/s, "
                    f"{weather['condition']}"
                )
                if self._repo:
                    try:
                        await self._repo.save_weather_reading(
                            temp_out=weather["temp_out"],
                            humidity_out=weather["humidity_out"],
                            condition=weather["condition"],
                            wind_speed=weather["wind_speed"],
                            ts=weather["ts"],
                        )
                    except Exception as e:
                        print(f"[OpenMeteo] Błąd zapisu do bazy: {e}")
            await asyncio.sleep(self._interval)
