from Ports.waterheater import WaterHeaterPort

class WaterHeaterService:
    def __init__(self, boiler: WaterHeaterPort):
        self._b = boiler

    async def refresh(self): await self._b.refresh()
    async def set_power(self, on: bool): await self._b.set_power(on)
    def get_power(self) -> bool: return self._b.get_power()
    async def set_target_temp(self, t: float): await self._b.set_target_temperature(t)
    def get_target_temp(self) -> float: return self._b.get_target_temperature()
    def get_mode(self) -> str: return self._b.get_mode_text()
    def get_current_temp(self) -> float: return self._b.get_current_temperature()
    async def set_mode(self, mode: str): await self._b.set_operation_mode(mode)
