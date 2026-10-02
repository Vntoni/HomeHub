from PySide6.QtCore import QObject, Signal
from App.climate_service import ClimateService
from App.sensor_service import SensorService
from App.water_heater_service import WaterHeaterService
from App.washer_service import WasherService
from App.heater_service import HeaterService
from Ports.washer import WasherSnapshot
from qasync import asyncSlot
from typing import Optional
import asyncio
import math


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

    boilerSettingsFinished = Signal(bool, str)
    acSettingsFinished = Signal(str, bool, str)
    acFanSpeedReceived = Signal(str, str)
    heaterSettingsFinished = Signal(str, bool, str)
    deviceSettingsReceived = Signal(str, str, dict)
    deviceSettingsFailed = Signal(str, str, str)
    devicePowerFinished = Signal(str, str, bool, str)

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

    # Sensors (czujniki Zigbee)
    sensorTempChanged = Signal(str, object)      # pokój, temperatura lub None
    sensorHumidityChanged = Signal(str, object)  # pokój, wilgotność lub None

    def __init__(self, climate: ClimateService, boiler: WaterHeaterService,
                 washer: WasherService, heater: Optional[HeaterService] = None, sensor: Optional[SensorService] = None):
        super().__init__()
        self._climate = climate
        self._boiler = boiler
        self._washer = washer
        self._heater = heater
        self._sensors = sensor
        self._boiler_online = False
        self._command_locks = {}

    def _command_lock(self, kind, room):
        return self._command_locks.setdefault((kind, room), asyncio.Lock())

    def _on_washer_snapshot(self, st: WasherSnapshot):
        self.washerOnlineChanged.emit(st.online)
        self.washerRemainingChanged.emit(
            int(st.remaining_minutes) if st.online and st.remaining_minutes is not None else -1)
        self.washerLastSeenChanged.emit(st.last_seen or "")

    async def shutdown(self):
        if self._sensors:
            await self._sensors.aclose()
        if self._washer:
            await self._washer.stop()

    # --- init/refresh
    async def init_all(self):
        if self._washer:
            await self._washer.start(self._on_washer_snapshot)
        # odśwież AC i boiler, oceń online
        try:
            await self._climate.refresh_all()
        except:
            print("Not working climate refresh")
        try:
            await self._boiler.refresh()
            self._boiler_online = True
            self.boilerOnlineChanged.emit(True)
        except Exception as exc:
            self._boiler_online = False
            self.boilerOnlineChanged.emit(False)
            print(f"Not working boiler refresh: {exc}")

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
        if self._sensors:
            try:
                for room in self._sensors.rooms():
                    self.sensorTempChanged.emit(room, self._sensors.get_temperature(room))
                    self.sensorHumidityChanged.emit(room, self._sensors.get_humidity(room))
            except Exception as e:
                print(f"Not working sensors refresh: {e}")

        try:
            online = self._climate.online_map()
            self.acSalonOnlineChanged.emit(bool(online.get("Salon")))
            self.acJadalniaOnlineChanged.emit(bool(online.get("Jadalnia")))
            # brak API na online boilera? spróbuj z refresh – błąd emituj False
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
    @asyncSlot(str)
    async def set_water_heater_mode(self, mode: str):
        await self._boiler.set_mode(mode)
        await self._boiler.refresh()
        self.modeOperating.emit(self._boiler.get_mode())

    @asyncSlot(float, str)
    async def apply_water_heater_settings(self, temp: float, mode: str):
        async with self._command_lock("boiler", "boiler"):
            try:
                self._validate_temperature(temp, 40, 65)
                if mode not in {"GREEN", "IMEMORY", "BOOST", "PROGRAM"}:
                    raise ValueError("Invalid boiler mode")
                async with asyncio.timeout(45):
                    await self._boiler.set_mode(mode)
                    await self._boiler.set_target_temp(temp)
                    await self._boiler.refresh()
                self.targetTemperatureReceived.emit("boiler", self._boiler.get_target_temp())
                self.modeOperating.emit(self._boiler.get_mode())
                self.waterTemp.emit("boiler", self._boiler.get_current_temp())
                self.powerStatus.emit(self._boiler.get_power())
                self._boiler_online = True
                self.boilerOnlineChanged.emit(True)
            except Exception:
                self.boilerSettingsFinished.emit(False, "Nie udało się zapisać lub odczytać ustawień. Odśwież stan urządzenia.")
            else:
                self.boilerSettingsFinished.emit(True, "Wysłano ustawienia i odświeżono odczyt. Chmura może potwierdzić zmianę z opóźnieniem.")

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


    @staticmethod
    def _optional_bool(value):
        if value is None:
            return None
        return value is True or getattr(value, "value", value) == "ON"

    def _settings(self, kind, room):
        if kind == "ac":
            return dict(target=self._climate.target_temp(room),
                        mode=self._climate.operating_mode(room),
                        fan_speed=self._climate.fan_speed(room),
                        economy=self._optional_bool(self._climate.economy(room)),
                        powerful=self._optional_bool(self._climate.powerful(room)),
                        quiet=self._optional_bool(self._climate.low_noise(room)))
        if kind == "boiler":
            return dict(target=self._boiler.get_target_temp(), mode=self._boiler.get_mode(),
                        current=self._boiler.get_current_temp())
        if kind == "heater" and self._heater:
            return dict(target=self._heater.get_target_temp(room), mode=self._heater.get_mode(room),
                        current=self._heater.get_current_temp(room))
        raise ValueError("Device unavailable")

    @asyncSlot(str, str)
    async def load_device_settings(self, kind, room):
        try:
            self.deviceSettingsReceived.emit(kind, room, self._settings(kind, room))
        except Exception:
            self.deviceSettingsFailed.emit(kind, room, "Nie udało się wczytać ustawień. Zamknij okno i odśwież urządzenia.")

    @asyncSlot()
    async def publish_dashboard(self):
        # Cached readings only. Explicit refresh_connection performs network reads.
        online = self._climate.online_map()
        self.acSalonOnlineChanged.emit(bool(online.get("Salon")))
        self.acJadalniaOnlineChanged.emit(bool(online.get("Jadalnia")))
        self.boilerOnlineChanged.emit(self._boiler_online)
        for room in online:
            try:
                self.tempIndoorChanged.emit(room, self._climate.temp_indoor(room))
                self.targetTemperatureReceived.emit(room, self._climate.target_temp(room))
                self.modeReceived.emit(room, self._climate.operating_mode(room))
            except Exception:
                continue
        try:
            self.waterTemp.emit("boiler", self._boiler.get_current_temp())
            self.targetTemperatureReceived.emit("boiler", self._boiler.get_target_temp())
            self.modeOperating.emit(self._boiler.get_mode())
            self.powerStatus.emit(self._boiler.get_power())
        except Exception:
            pass
        if self._heater:
            for room, connected in self._heater.online_map().items():
                self.heaterOnlineChanged.emit(room, connected)
                try:
                    self.heaterCurrentTempChanged.emit(room, self._heater.get_current_temp(room))
                    self.heaterTargetTempChanged.emit(room, self._heater.get_target_temp(room))
                    self.heaterModeChanged.emit(room, self._heater.get_mode(room))
                    self.heaterPowerChanged.emit(room, self._heater.get_power(room))
                except Exception:
                    continue

    @staticmethod
    def _validate_temperature(temp, minimum, maximum):
        if not math.isfinite(temp) or not minimum <= temp <= maximum:
            raise ValueError("Invalid temperature")

    @asyncSlot(str, float, str, bool, bool, bool, str)
    async def apply_ac_settings(self, room, temp, mode, economy, powerful, quiet, fan_speed=""):
        async with self._command_lock("ac", room):
            try:
                if mode not in {"OFF", "FAN"}:
                    self._validate_temperature(temp, 10, 30)
                if fan_speed and fan_speed not in {"QUIET", "LOW", "MEDIUM", "HIGH", "AUTO"}:
                    raise ValueError("Invalid fan speed")
                if mode not in {"COOL", "HEAT", "FAN", "DRY", "AUTO", "OFF"}:
                    raise ValueError("Invalid mode")
                async with asyncio.timeout(45):
                    if mode == "OFF":
                        await self._climate.turn_off(room)
                    else:
                        await self._climate.set_operating_mode(room, mode)
                        if mode != "FAN":
                            await self._climate.set_target_temp(room, temp)
                        if fan_speed:
                            await self._climate.set_fan_speed(room, fan_speed)
                        if self._climate.economy(room) is not None:
                            await self._climate.set_economy(room, "ON" if economy and not powerful else "OFF")
                        if self._climate.powerful(room) is not None:
                            await self._climate.set_powerful(room, "ON" if powerful else "OFF")
                        if self._climate.low_noise(room) is not None:
                            await self._climate.set_low_noise(room, "ON" if quiet else "OFF")
                        await self._climate.turn_on(room)
                    await self._climate.refresh(room)
                self.acFanSpeedReceived.emit(room, self._climate.fan_speed(room))
                await self.publish_dashboard()
            except Exception:
                self.acSettingsFinished.emit(room, False, "Nie udało się zapisać lub odczytać wszystkich ustawień. Odśwież stan urządzenia.")
            else:
                self.acSettingsFinished.emit(room, True, "Wysłano ustawienia i odświeżono odczyt. Chmura może potwierdzić zmianę z opóźnieniem.")

    @asyncSlot(str, float, str, int)
    async def apply_heater_settings(self, room, temp, mode, duration):
        async with self._command_lock("heater", room):
            try:
                self._validate_temperature(temp, 7, 28)
                if not self._heater or mode not in {"manual", "program"} or duration not in {30, 60, 120, 240}:
                    raise ValueError("Invalid heater settings")
                async with asyncio.timeout(45):
                    await self._heater.set_mode(room, mode)
                    await self._heater.set_target_temp(room, temp, duration)
                    await self._heater.refresh(room)
                await self.publish_dashboard()
            except Exception:
                self.heaterSettingsFinished.emit(room, False, "Nie udało się zapisać lub odczytać wszystkich ustawień. Odśwież stan urządzenia.")
            else:
                self.heaterSettingsFinished.emit(room, True, "Wysłano ustawienia i odświeżono odczyt. Chmura może potwierdzić zmianę z opóźnieniem.")

    @asyncSlot(str, str, bool)
    async def apply_device_power(self, kind, room, on):
        async with self._command_lock(kind, room):
            try:
                async with asyncio.timeout(45):
                    if kind == "ac":
                        await (self._climate.turn_on(room) if on else self._climate.turn_off(room))
                        await self._climate.refresh(room)
                    elif kind == "boiler":
                        await self._boiler.set_power(on)
                        await self._boiler.refresh()
                    elif kind == "heater" and self._heater:
                        await (self._heater.turn_on(room) if on else self._heater.turn_off(room))
                        await self._heater.refresh(room)
                    else:
                        raise ValueError("Device unavailable")
            except Exception:
                self.devicePowerFinished.emit(kind, room, False, "Błąd polecenia lub odczytu. Odśwież urządzenie.")
            else:
                self.devicePowerFinished.emit(kind, room, True, "Wysłano polecenie i odświeżono odczyt.")
            finally:
                await self.publish_dashboard()
