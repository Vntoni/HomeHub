from Ports.waterheater import WaterHeaterPort
from App.device_snapshot import DeviceSnapshot

class AristonBoilerAdapter(WaterHeaterPort):
    def __init__(self, client):
        self._c = client
        self._snapshot = None

    async def refresh(self) -> None:
        await self._c.async_update_state()
        await self._c.async_update_energy()
        power = self._c.water_heater_power_value
        if power is None:
            raise ValueError("Missing boiler power")
        snapshot = DeviceSnapshot(float(self._c.water_heater_current_temperature),
                                  float(self._c.water_heater_target_temperature),
                                  str(self._c.water_heater_current_mode_text), bool(power))
        self._snapshot = snapshot

    async def set_power(self, on: bool) -> None:
        await self._c.async_set_power(on)

    def get_power(self) -> bool:
        return self._snapshot.power if self._snapshot else False

    async def set_target_temperature(self, temp_c: float) -> None:
        await self._c.async_set_water_heater_temperature(temp_c)

    def get_target_temperature(self) -> float:
        return self._snapshot.target if self._snapshot else float("nan")

    def get_mode_text(self) -> str:
        return self._snapshot.mode if self._snapshot else "unknown"

    def get_current_temperature(self) -> float:
        return self._snapshot.current if self._snapshot else float("nan")

    async def set_operation_mode(self, mode: str) -> None:
        await self._c.async_set_water_heater_operation_mode(mode)
