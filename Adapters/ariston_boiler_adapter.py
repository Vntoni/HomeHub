from Ports.waterheater import WaterHeaterPort

class AristonBoilerAdapter(WaterHeaterPort):
    def __init__(self, client):
        self._c = client

    async def refresh(self) -> None:
        await self._c.async_update_state()
        await self._c.async_update_energy()

    async def set_power(self, on: bool) -> None:
        await self._c.async_set_power(on)

    def get_power(self) -> bool:
        return bool(self._c.water_heater_power_value)

    async def set_target_temperature(self, temp_c: float) -> None:
        await self._c.async_set_water_heater_temperature(temp_c)

    def get_target_temperature(self) -> float:
        return float(self._c.water_heater_target_temperature)

    def get_mode_text(self) -> str:
        return str(self._c.water_heater_current_mode_text)

    def get_current_temperature(self) -> float:
        return float(self._c.water_heater_current_temperature)

    async def set_operation_mode(self, mode: str) -> None:
        await self._c.async_set_water_heater_operation_mode(mode)