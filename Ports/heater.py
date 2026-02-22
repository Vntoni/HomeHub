from typing import Protocol

class HeaterPort(Protocol):
    """Port dla elektrycznego grzejnika (Cozy Touch)"""

    async def refresh(self) -> None:
        """Odśwież stan grzejnika z API"""
        ...

    async def set_power(self, on: bool) -> None:
        """Włącz/wyłącz grzejnik"""
        ...

    def get_power(self) -> bool:
        """Pobierz status zasilania"""
        ...

    async def set_target_temperature(self, temp_c: float, duration_minutes: int = 120) -> None:
        """Ustaw temperaturę docelową"""
        ...

    def get_target_temperature(self) -> float:
        """Pobierz temperaturę docelową"""
        ...

    def get_current_temperature(self) -> float:
        """Pobierz aktualną temperaturę"""
        ...

    async def set_mode(self, mode: str) -> None:
        """Ustaw tryb pracy (np. comfort, eco, frost_protection, auto)"""
        ...

    def get_mode(self) -> str:
        """Pobierz aktualny tryb pracy"""
        ...

    def is_online(self) -> bool:
        """Sprawdź czy grzejnik jest online"""
        ...
