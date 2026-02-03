from typing import Dict

from pyairstage.constants import OperationMode, BooleanProperty

from Ports.ac import ACUnitPort

class ClimateService:
    def __init__(self, units: Dict[str, ACUnitPort]):
        self._units = units  # {"Salon": ac1, "Jadalnia": ac2}

    def _get(self, room: str) -> ACUnitPort:
        if room not in self._units:
            raise KeyError(f"Unknown room: {room}")
        return self._units[room]

    async def refresh_all(self) -> None:
        for ac in self._units.values():
            await ac.refresh()

    async def turn_on(self, room: str) -> None:
        await self._get(room).turn_on()

    async def turn_off(self, room: str) -> None:
        await self._get(room).turn_off()

    def temp_indoor(self, room: str) -> float:
        return self._get(room).get_display_temperature()

    def target_temp(self, room: str) -> float:
        return self._get(room).get_target_temperature()

    async def set_target_temp(self, room: str, temp: float) -> None:
        await self._get(room).set_target_temperature(temp)

    def economy(self, room: str) -> bool:
        return self._get(room).get_economy_mode()

    async def set_economy(self, room: str, mode: str) -> None:
        mode = BooleanProperty[mode]
        await self._get(room).set_economy_mode(mode)

    def powerful(self, room: str) -> bool:
        return self._get(room).get_powerful_mode()

    async def set_powerful(self, room: str, mode: str) -> None:
        mode = BooleanProperty[mode]
        await self._get(room).set_powerful_mode(mode)

    def low_noise(self, room: str) -> bool:
        return self._get(room).get_outdoor_low_noise()

    async def set_low_noise(self, room: str, mode: str) -> None:
        mode = BooleanProperty[mode]
        print(f"Setting low noise for room: {room} with mode: {mode}")
        await self._get(room).set_outdoor_low_noise(mode)

    def operating_mode(self, room: str) -> str:
        return self._get(room).get_operating_mode()

    async def set_operating_mode(self, room: str, mode: str) -> None:
        mode = OperationMode[mode]
        await self._get(room).set_operation_mode(mode)

    def online_map(self) -> dict:
        return {room: ac.is_online() for room, ac in self._units.items()}



