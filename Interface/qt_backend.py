from PySide6.QtCore import QObject, Signal, Slot
from App.climate_service import ClimateService
from App.water_heater_service import WaterHeaterService
from App.washer_service import WasherService
from Ports.washer import WasherSnapshot
from qasync import asyncSlot
import asyncio


class QtHomeBackend(QObject):
    # statusy online
    ready = Signal(bool)
    acSalonOnlineChanged = Signal(bool)
    acJadalniaOnlineChanged = Signal(bool)
    boilerOnlineChanged = Signal(bool)

    # AC
    tempIndoorChanged = Signal(str, float)
    modeReceived = Signal(str, str)
    targetTemperatureReceived = Signal(str, float)
    economyReceived = Signal(str, bool)
    powerfulReceived = Signal(str, bool)
    lowNoiseReceived = Signal(str, bool)

    # Boiler
    waterTemp = Signal(str, float)
    modeOperating = Signal(str)
    powerStatus = Signal(bool)

    # Washer
    washerOnlineChanged = Signal(bool)
    washerRemainingChanged = Signal(int)
    washerLastSeenChanged = Signal(str)

    def __init__(self, climate: ClimateService, boiler: WaterHeaterService, washer: WasherService):
        super().__init__()
        self._climate = climate
        self._boiler = boiler
        self._washer = washer
        # self.start_washer()
        # start monitor pralki (callback -> emit sygnałów)
    # async def start_washer(self):
    #     try:
    #         await self._washer.start(self._on_washer_snapshot)
    #     except Exception as e:
    #         print(f"Error starting washer service: {e}")

    def _on_washer_snapshot(self, st: WasherSnapshot):
        self.washerOnlineChanged.emit(st.online)
        if st.remaining_minutes is not None:
            self.washerRemainingChanged.emit(int(st.remaining_minutes))
        if st.last_seen is not None:
            self.washerLastSeenChanged.emit(st.last_seen)

    # --- init/refresh
    async def init_all(self):
        # odśwież AC i boiler, oceń online
        try:
            await self._climate.refresh_all()
        except:
            print("Not working climate refresh")
        try:
            await self._boiler.refresh()
        except:
            print("Not working boiler refresh")
        try:
            online = self._climate.online_map()
            self.acSalonOnlineChanged.emit(bool(online.get("Salon")))
            self.acJadalniaOnlineChanged.emit(bool(online.get("Jadalnia")))
            # brak API na online boilera? spróbuj z refresh – błąd emituj False
            self.boilerOnlineChanged.emit(True)  # jeśli refresh OK
            self.ready.emit(True)
        except Exception as e:
            print(f"Error during init_all: {e}")

    @asyncSlot()
    async def refresh_connection(self):
        await self.init_all()

    # --- AC
    @asyncSlot(str)
    async def turn_on_ac(self, room: str): await self._climate.turn_on(room)

    @asyncSlot(str)
    async def turn_off_ac(self, room: str): await self._climate.turn_off(room)

    @asyncSlot(str)
    async def get_temp_indoor(self, room: str):
        self.tempIndoorChanged.emit(room, self._climate.temp_indoor(room))

    @asyncSlot(str)
    async def get_target_temp(self, room: str):
        self.targetTemperatureReceived.emit(room, self._climate.target_temp(room))

    @asyncSlot(str, float)
    async def set_target_temp(self, room: str, temp: float):
        await self._climate.set_target_temp(room, temp)
        self.targetTemperatureReceived.emit(room, self._climate.target_temp(room))

    @asyncSlot(str)
    async def get_economy(self, room: str):
        self.economyReceived.emit(room, self._climate.economy(room))

    @asyncSlot(str, str)
    async def set_economy(self, room: str, mode: str):
        await self._climate.set_economy(room, mode)
        self.economyReceived.emit(room, self._climate.economy(room))

    @asyncSlot(str)
    async def get_powerful(self, room: str):
        self.powerfulReceived.emit(room, self._climate.powerful(room))

    @asyncSlot(str, str)
    async def set_powerful(self, room: str, mode: str):
        await self._climate.set_powerful(room, mode)
        self.powerfulReceived.emit(room, self._climate.powerful(room))

    @asyncSlot(str)
    async def get_low_noise(self, room: str):
        self.lowNoiseReceived.emit(room, self._climate.low_noise(room))

    @asyncSlot(str, str)
    async def set_low_noise(self, room: str, mode: str):
        print(f"Setting low noise for room: {room}, MODE: {mode}")
        await self._climate.set_low_noise(room, mode)
        self.lowNoiseReceived.emit(room, self._climate.low_noise(room))

    @asyncSlot(str)
    async def get_mode_operation(self, room: str):
        print(f"Getting mode for room: {room}, MODE: {self._climate.operating_mode(room)}")
        self.modeReceived.emit(room, self._climate.operating_mode(room))

    @asyncSlot(str, str)
    async def set_mode_operation(self, room: str, mode: str):
        await self._climate.set_operating_mode(room, mode)
        self.modeReceived.emit(room, self._climate.operating_mode(room))

    # --- Boiler
    @asyncSlot(bool)
    async def set_water_heater_power(self, power: bool):
        await self._boiler.set_power(power)

    @asyncSlot()
    async def get_water_heater_power(self):
        self.powerStatus.emit(self._boiler.get_power())

    @asyncSlot(float)
    async def set_water_target_temp(self, temp: float):
        await self._boiler.set_target_temp(temp)

    @asyncSlot()
    async def get_water_target_temp(self):
        self.targetTemperatureReceived.emit("boiler", self._boiler.get_target_temp())

    @asyncSlot()
    async def get_water_heater_mode(self):
        self.modeOperating.emit(self._boiler.get_mode())

    @asyncSlot()
    async def get_water_temp(self):
        self.waterTemp.emit("boiler", self._boiler.get_current_temp())

