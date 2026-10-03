from typing import Dict
import asyncio

from pyairstage.constants import OperationMode, BooleanProperty, BooleanDescriptors, FanSpeed

from Ports.ac import ACUnitPort


async def confirm_ac_power(service, room, on, *, attempts=4, interval=2.0):
    """Retry readbacks only; never resend a command after an uncertain result."""
    last_error = None
    for attempt in range(attempts):
        try:
            await service.refresh(room)
            mode = service.operating_mode(room)
            if (on and mode in {"AUTO", "COOL", "DRY", "FAN", "HEAT"}) or (not on and mode == "OFF"):
                return
        except Exception as exc:
            last_error = exc
        if attempt + 1 < attempts:
            await asyncio.sleep(interval)
    raise RuntimeError("AC power was not confirmed by a fresh reading") from last_error

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

    async def refresh(self, room: str) -> None:
        await self._get(room).refresh()

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

    def economy(self, room: str) -> BooleanDescriptors:
        return self._get(room).get_economy_mode()

    async def set_economy(self, room: str, mode: str) -> None:
        mode = BooleanProperty[mode]
        await self._get(room).set_economy_mode(mode)

    def powerful(self, room: str) -> BooleanDescriptors:
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

    def fan_speed(self, room: str) -> str:
        return self._get(room).get_fan_speed()

    def airflow_options(self, room: str) -> list[str]:
        return self._get(room).get_airflow_options()

    def airflow(self, room: str) -> str:
        return self._get(room).get_airflow()

    async def set_airflow(self, room: str, value: str) -> None:
        await self._get(room).set_airflow(value)

    async def set_fan_speed(self, room: str, speed: str) -> None:
        await self._get(room).set_fan_speed(FanSpeed[speed])

    def operating_mode(self, room: str) -> str:
        return self._get(room).get_operating_mode()

    async def set_operating_mode(self, room: str, mode: str) -> None:
        mode = OperationMode[mode]
        await self._get(room).set_operation_mode(mode)

    def online_map(self) -> dict:
        return {room: ac.is_online() for room, ac in self._units.items()}

