from typing import Any
from Ports.ac import ACUnitPort
from pyairstage.airstageAC import AirstageAC, ApiCloud

class AirstageACAdapter(ACUnitPort):
    def __init__(self, device_id: str, api_cloud: Any, impl_cls):
        self.device_id = device_id
        self._api = api_cloud
        self._impl = impl_cls(device_id, api_cloud)   # np. pyairstage.AirstageAC

    async def refresh(self) -> None:
        await self._impl.refresh_parameters()

    async def turn_on(self) -> None:
        await self._impl.turn_on()

    async def turn_off(self) -> None:
        await self._impl.turn_off()

    def is_online(self) -> bool:
        # unikamy ._cache w idealnym świecie; jeśli brak API, opakuj i ujednolić
        st = getattr(self._impl, "_cache", {}).get("connectionStatus", "Offline")
        return st == "Online"

    def get_display_temperature(self) -> float:
        return self._impl.get_display_temperature()

    def get_target_temperature(self) -> float:
        return self._impl.get_target_temperature()

    async def set_target_temperature(self, temp: float) -> None:
        await self._impl.set_target_temperature(temp)

    def get_economy_mode(self) -> bool:
        return self._impl.get_economy_mode()

    async def set_economy_mode(self, mode: str) -> None:
        await self._impl.set_economy_mode(mode)

    def get_powerful_mode(self) -> bool:
        return self._impl.get_powerful_mode()

    async def set_powerful_mode(self, mode: str) -> None:
        await self._impl.set_powerful_mode(mode)

    def get_outdoor_low_noise(self) -> bool:
        return self._impl.get_outdoor_low_noise()

    async def set_outdoor_low_noise(self, mode: str) -> None:
        print(f"W koncu mode: {mode}")
        await self._impl.set_outdoor_low_noise(mode)

    def get_operating_mode(self) -> str:
        return getattr(self._impl.get_operating_mode(), "value", "UNKNOWN")

    async def set_operation_mode(self, mode: str) -> None:
        await self._impl.set_operation_mode(mode)


