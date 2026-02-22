from PySide6.QtCore import QObject, Signal
from App.climate_service import ClimateService
from App.water_heater_service import WaterHeaterService
from App.washer_service import WasherService
from App.heater_service import HeaterService
from Ports.washer import WasherSnapshot
from qasync import asyncSlot
from typing import Optional


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

    # Heaters (grzejniki)
    heaterOnlineChanged = Signal(str, bool)  # pokój, status
    heaterCurrentTempChanged = Signal(str, float)  # pokój, temp
    heaterTargetTempChanged = Signal(str, float)  # pokój, temp
    heaterModeChanged = Signal(str, str)  # pokój, tryb
    heaterPowerChanged = Signal(str, bool)  # pokój, on/off

    def __init__(self, climate: ClimateService, boiler: WaterHeaterService,
                 washer: WasherService, heater: Optional[HeaterService] = None):
        super().__init__()
        self._climate = climate
        self._boiler = boiler
        self._washer = washer
        self._heater = heater
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

        # Odśwież grzejniki jeśli są dostępne
        if self._heater:
            try:
                await self._heater.refresh_all()

                # Emituj statusy online
                online_map = self._heater.online_map()

                for room, is_online in online_map.items():
                    self.heaterOnlineChanged.emit(room, is_online)

                # Emituj temperatury i tryby dla każdego pokoju
                for room in online_map.keys():
                    try:
                        # Temperatura aktualna
                        current_temp = self._heater.get_current_temp(room)
                        self.heaterCurrentTempChanged.emit(room, current_temp)

                        # Temperatura docelowa
                        target_temp = self._heater.get_target_temp(room)
                        self.heaterTargetTempChanged.emit(room, target_temp)

                        # Tryb pracy
                        mode = self._heater.get_mode(room)
                        self.heaterModeChanged.emit(room, mode)

                        # Status zasilania
                        power = self._heater.get_power(room)
                        self.heaterPowerChanged.emit(room, power)
                    except Exception as e:
                        print(f"Error emitting heater data for {room}: {e}")

            except Exception as e:
                print(f"Not working heater refresh: {e}")
                import traceback
                traceback.print_exc()

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

    # --- Heaters (grzejniki elektryczne) ---
    @asyncSlot(str)
    async def turn_on_heater(self, room: str):
        """Włącz grzejnik w danym pokoju"""
        if self._heater:
            await self._heater.turn_on(room)
            self.heaterPowerChanged.emit(room, True)

    @asyncSlot(str)
    async def turn_off_heater(self, room: str):
        """Wyłącz grzejnik w danym pokoju"""
        if self._heater:
            await self._heater.turn_off(room)
            self.heaterPowerChanged.emit(room, False)

    @asyncSlot(str)
    async def get_heater_power(self, room: str):
        """Pobierz status zasilania grzejnika"""
        if self._heater:
            self.heaterPowerChanged.emit(room, self._heater.get_power(room))

    @asyncSlot(str, float, int)
    async def set_heater_target_temp(self, room: str, temp: float, duration_minutes: int = 120):
        """
        Ustaw temperaturę docelową grzejnika

        Args:
            room: Nazwa pokoju
            temp: Temperatura w °C
            duration_minutes: Czas trwania (dla trybu wyjątku), domyślnie 120 min
        """
        if self._heater:
            await self._heater.set_target_temp(room, temp, duration_minutes)
            self.heaterTargetTempChanged.emit(room, self._heater.get_target_temp(room))

    @asyncSlot(str)
    async def get_heater_target_temp(self, room: str):
        """Pobierz temperaturę docelową grzejnika"""
        if self._heater:
            self.heaterTargetTempChanged.emit(room, self._heater.get_target_temp(room))

    @asyncSlot(str)
    async def get_heater_current_temp(self, room: str):
        """Pobierz aktualną temperaturę z grzejnika"""
        if self._heater:
            self.heaterCurrentTempChanged.emit(room, self._heater.get_current_temp(room))

    @asyncSlot(str, str)
    async def set_heater_mode(self, room: str, mode: str):
        """
        Ustaw tryb pracy grzejnika
        mode: comfort, eco, frost_protection, auto, away
        """
        if self._heater:
            await self._heater.set_mode(room, mode)
            self.heaterModeChanged.emit(room, self._heater.get_mode(room))

    @asyncSlot(str)
    async def get_heater_mode(self, room: str):
        """Pobierz tryb pracy grzejnika"""
        if self._heater:
            self.heaterModeChanged.emit(room, self._heater.get_mode(room))

