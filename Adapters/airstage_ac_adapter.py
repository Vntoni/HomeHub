from typing import Any
from copy import deepcopy
from inspect import iscoroutinefunction
from pyairstage.constants import FanSpeed
from Ports.ac import ACUnitPort
from pyairstage.airstageAC import AirstageAC, ApiCloud, BooleanDescriptors

class AirstageACAdapter(ACUnitPort):
    def __init__(self, device_id: str, api_cloud: Any, impl_cls):
        self.device_id = device_id
        self._api = api_cloud
        self._impl = impl_cls(device_id, api_cloud)   # np. pyairstage.AirstageAC
        self._confirmed_mode = None

    async def refresh(self) -> None:
        refresh = self._impl.refresh_parameters
        if iscoroutinefunction(refresh):
            # Preserve SDKs with the older asynchronous refresh contract.
            await refresh()
            self._record_fresh_mode()
            return
        # pyairstage 3.2.2 fetches devices asynchronously but parses a supplied
        # payload synchronously. Its no-argument parser cannot perform that I/O.
        devices = await self._api.get_devices()
        if not isinstance(devices, dict) or self.device_id not in devices:
            raise ValueError("AC missing from device response")
        data = devices[self.device_id]
        if not isinstance(data, dict) or not isinstance(data.get("parameters"), list):
            raise ValueError("Invalid AC parameter response")
        if any(not isinstance(p, dict) or "name" not in p or "value" not in p
               for p in data["parameters"]):
            raise ValueError("Invalid AC parameter entry")
        # The parser modifies the mapping; keep the transport response untouched.
        refresh(data=deepcopy(data))
        self._record_fresh_mode()

    async def turn_on(self) -> None:
        self._capture_mode_before_write()
        await self._impl.turn_on()

    async def turn_off(self) -> None:
        self._capture_mode_before_write()
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

    def get_economy_mode(self) -> BooleanDescriptors:
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
        await self._impl.set_outdoor_low_noise(mode)

    def get_fan_speed(self) -> str:
        try:
            return getattr(self._impl.get_fan_speed(), "value", "UNKNOWN")
        except (TypeError, ValueError, KeyError):
            # Missing/unknown cached fan readings must not prevent other settings.
            return "UNKNOWN"

    async def set_fan_speed(self, speed: FanSpeed) -> None:
        await self._impl.set_fan_speed(speed)

    def get_operating_mode(self) -> str:
        if self._confirmed_mode is None:
            self._confirmed_mode = self._read_mode()
        return self._confirmed_mode

    def _read_mode(self):
        try:
            return getattr(self._impl.get_operating_mode(), "value", "UNKNOWN")
        except (TypeError, ValueError, KeyError):
            return "UNKNOWN"

    def _capture_mode_before_write(self):
        # SDK writes mutate its cache before the cloud confirms device state.
        if self._confirmed_mode is None:
            self._confirmed_mode = self._read_mode()

    def _record_fresh_mode(self):
        mode = self._read_mode()
        if mode not in {"OFF", "AUTO", "COOL", "DRY", "FAN", "HEAT"}:
            raise ValueError("AC response does not contain a valid power/mode reading")
        self._confirmed_mode = mode

    async def set_operation_mode(self, mode: str) -> None:
        self._capture_mode_before_write()
        await self._impl.set_operation_mode(mode)
