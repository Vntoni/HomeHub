from Ports.heater import HeaterPort
from typing import Dict

class HeaterService:
    """Service zarządzający wieloma grzejnikami"""

    def __init__(self, heaters: Dict[str, HeaterPort]):
        """
        Args:
            heaters: Słownik {nazwa_pokoju: HeaterPort}
                    np. {"Salon": heater_salon, "Sypialnia": heater_sypialnia}
        """
        self._heaters = heaters

    async def refresh_all(self) -> None:
        """Odśwież wszystkie grzejniki"""
        for heater in self._heaters.values():
            await heater.refresh()

    async def refresh(self, room: str) -> None:
        """Odśwież konkretny grzejnik"""
        await self._heaters[room].refresh()

    async def turn_on(self, room: str) -> None:
        """Włącz grzejnik w pokoju"""
        await self._heaters[room].set_power(True)

    async def turn_off(self, room: str) -> None:
        """Wyłącz grzejnik w pokoju"""
        await self._heaters[room].set_power(False)

    def get_power(self, room: str) -> bool:
        """Pobierz status zasilania grzejnika"""
        return self._heaters[room].get_power()

    async def set_target_temp(self, room: str, temp: float, duration_minutes: int = 120) -> None:
        """
        Ustaw temperaturę docelową

        Args:
            room: Nazwa pokoju
            temp: Temperatura w °C
            duration_minutes: Czas trwania (dla trybu wyjątku), domyślnie 120 min
        """
        await self._heaters[room].set_target_temperature(temp, duration_minutes)

    def get_target_temp(self, room: str) -> float:
        """Pobierz temperaturę docelową"""
        return self._heaters[room].get_target_temperature()

    def get_current_temp(self, room: str) -> float:
        """Pobierz aktualną temperaturę"""
        return self._heaters[room].get_current_temperature()

    async def set_mode(self, room: str, mode: str) -> None:
        """Ustaw tryb pracy grzejnika"""
        await self._heaters[room].set_mode(mode)

    def get_mode(self, room: str) -> str:
        """Pobierz tryb pracy grzejnika"""
        return self._heaters[room].get_mode()

    def is_online(self, room: str) -> bool:
        """Sprawdź czy grzejnik jest online"""
        return self._heaters[room].is_online()

    def online_map(self) -> Dict[str, bool]:
        """Zwróć mapę statusów online wszystkich grzejników"""
        return {room: heater.is_online() for room, heater in self._heaters.items()}
