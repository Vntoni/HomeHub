from PySide6.QtCore import QObject, Signal, Property
from Ports.respeaker import RespeakerStatus
from Interface.qt_audio_probe import AudioProbeController
from App.climate_service import ClimateService, confirm_ac_power
from App.sensor_service import SensorService
from App.water_heater_service import WaterHeaterService
from App.washer_service import WasherService
from App.heater_service import HeaterService
from Ports.washer import WasherSnapshot
from qasync import asyncSlot
from typing import Optional
import asyncio
import math
import inspect
from functools import wraps
from inspect import signature
from App.operations import OperationCoordinator, OperationBusy


def device_operation(kind=None, finished=None):
    """Keep the real transport owned after a UI waiter times out."""
    def decorate(method):
        method_signature = signature(method)
        @wraps(method)
        async def guarded(self, *args, **kwargs):
            arguments = method_signature.bind(self, *args, **kwargs).arguments
            device_kind = kind or arguments["kind"]
            room = arguments.get("room", "boiler")
            # Preserve normal sequential commands for a room. After a timeout,
            # the registry independently rejects work while its transport lives.
            async with self._command_lock("request:" + device_kind, room):
                try:
                    return await self._operations.run(
                        self._operation_key(device_kind, room),
                        lambda: method(self, *args, **kwargs), timeout=self._command_timeout,
                        on_late_done=lambda: self._reconcile(device_kind, room))
                except (TimeoutError, OperationBusy, RuntimeError):
                    self._set_device_stale(device_kind, room, True)
                    if finished is None:
                        raise
                    message = "Nie potwierdzono operacji. Urządzenie może nadal wykonywać polecenie; poczekaj na odczyt stanu."
                    signal = getattr(self, finished)
                    if finished == "devicePowerFinished":
                        signal.emit(device_kind, room, False, message)
                    elif device_kind == "boiler":
                        signal.emit(False, message)
                    else:
                        signal.emit(room, False, message)
        return guarded
    return decorate


class ACSettingsBlocked(ValueError):
    """Settings require a confirmed active operating mode."""


class QtHomeBackend(QObject):
    @Property(QObject, constant=True)
    def audioProbe(self):
        return self._audio_probe

    respeakerStatusChanged = Signal()

    @Property(bool, notify=respeakerStatusChanged)
    def respeakerConnected(self):
        return self._respeaker_status.connected

    @Property(str, notify=respeakerStatusChanged)
    def respeakerStatusText(self):
        return self._respeaker_status.message

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
    acAirflowReceived = Signal(str, str)
    heaterSettingsFinished = Signal(str, bool, str)
    deviceSettingsReceived = Signal(str, str, dict)
    deviceSettingsFailed = Signal(str, str, str)
    devicePowerFinished = Signal(str, str, bool, str)
    deviceOperationBusyChanged = Signal(str, str, bool)
    deviceStaleChanged = Signal(str, str, bool)

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
    sensorTempChanged = Signal(str, "QVariant")      # pokój, temperatura lub None
    sensorHumidityChanged = Signal(str, "QVariant")  # pokój, wilgotność lub None

    def __init__(self, climate: ClimateService, boiler: WaterHeaterService,
                 washer: WasherService, heater: Optional[HeaterService] = None, sensor: Optional[SensorService] = None,
                 respeaker=None, audio_factory=None, transcriber=None):
        super().__init__()
        self._climate = climate
        self._boiler = boiler
        self._washer = washer
        self._heater = heater
        self._sensors = sensor
        self._respeaker = respeaker
        self._respeaker_status = RespeakerStatus()
        self._respeaker_task = None
        self._audio_probe = AudioProbeController(audio_factory, self, transcriber=transcriber)
        self._boiler_online = False
        self._command_locks = {}
        self._command_timeout = 45
        self._read_timeout = 30
        self._operations = OperationCoordinator(self._operation_busy)
        self._device_stale = {}
        self._lifecycle_tasks = set()
        self._lifecycle_resources = []
        self._shutdown_started = False
        self._shutdown_task = None
        self._refresh_task = None

    def register_task(self, task):
        """Register a background task owned by the application lifecycle."""
        self._lifecycle_tasks.add(task)
        task.add_done_callback(self._lifecycle_tasks.discard)
        return task

    def _on_respeaker_status(self, status):
        if not self._shutdown_started and status != self._respeaker_status:
            self._respeaker_status = status
            self._audio_probe.set_connected(status.connected)
            self.respeakerStatusChanged.emit()

    def _start_respeaker_monitor(self):
        if self._respeaker is not None and self._respeaker_task is None and not self._shutdown_started:
            self._respeaker_task = self.register_task(
                asyncio.create_task(self._respeaker.run(self._on_respeaker_status)))

    def register_resource(self, resource):
        """Register an async/sync-close resource for deterministic shutdown."""
        if resource is not None and resource not in self._lifecycle_resources:
            self._lifecycle_resources.append(resource)
        return resource

    def _operation_key(self, kind, room):
        # Atlantic shares mutable client state and authentication across rooms.
        return (kind, "shared" if kind == "heater" else room)

    def _operation_busy(self, key, busy):
        kind, room = key
        rooms = self._heater.online_map() if kind == "heater" and self._heater else (room,)
        for device_room in rooms:
            self.deviceOperationBusyChanged.emit(kind, device_room, busy)

    async def _read_device(self, kind, room):
        async def read():
            await self._refresh_device_state(kind, room)
        try:
            await self._operations.run(self._operation_key(kind, room), read,
                                       timeout=self._read_timeout, read=(kind, room))
        except TimeoutError:
            self._set_device_stale(kind, room, True)
            raise

    async def _refresh_device_state(self, kind, room):
        """Read inside an already owned operation, then publish freshness."""
        try:
            if kind == "ac":
                await self._climate.refresh(room)
            elif kind == "boiler":
                await self._boiler.refresh()
            elif kind == "heater" and self._heater:
                await self._heater.refresh(room)
            else:
                raise ValueError("Device unavailable")
        except Exception:
            if kind == "boiler":
                self._boiler_online = False
            self._set_device_stale(kind, room, True)
            raise
        else:
            if kind == "boiler":
                self._boiler_online = True
            self._set_device_stale(kind, room, False)

    def _set_device_stale(self, kind, room, stale):
        key = (kind, room)
        stale = bool(stale)
        if self._device_stale.get(key, False) == stale:
            return
        self._device_stale[key] = stale
        self.deviceStaleChanged.emit(kind, room, stale)

    async def _reconcile(self, kind, room):
        await self._read_device(kind, room)
        await self.publish_dashboard()

    def _command_lock(self, kind, room):
        return self._command_locks.setdefault((kind, room), asyncio.Lock())

    def _on_washer_snapshot(self, st: WasherSnapshot):
        self.washerOnlineChanged.emit(st.online)
        self.washerRemainingChanged.emit(
            int(st.remaining_minutes) if st.online and st.remaining_minutes is not None else -1)
        self.washerLastSeenChanged.emit(st.last_seen or "")

    async def shutdown(self):
        await self._audio_probe.aclose()  # Stop audio and reap STT before device waits.
        if self._shutdown_task is None:
            self._shutdown_task = asyncio.create_task(self._shutdown_resources())
        await asyncio.shield(self._shutdown_task)

    async def _shutdown_resources(self):
        self._shutdown_started = True
        errors = []
        async def attempt(close):
            try:
                if inspect.iscoroutinefunction(close):
                    await close()
                else:
                    result = await asyncio.to_thread(close)
                    if inspect.isawaitable(result):
                        await result
            except Exception as exc:
                errors.append(exc)

        tasks = list(self._lifecycle_tasks)
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            errors.extend(result for result in results if isinstance(result, Exception))
        await attempt(self._operations.close)
        if self._washer:
            await attempt(self._washer.stop)
        # SensorService.aclose drains accepted writes; it must precede DB close.
        resources = [self._sensors, *reversed(self._lifecycle_resources)]
        seen = set()
        for resource in resources:
            if resource is None or id(resource) in seen:
                continue
            seen.add(id(resource))
            close = getattr(resource, "aclose", None) or getattr(resource, "close", None)
            if callable(close):
                await attempt(close)
        if errors:
            raise ExceptionGroup("Application shutdown failed", errors)

    # --- init/refresh
    async def init_all(self):
        self._start_respeaker_monitor()
        if self._washer:
            await self._washer.start(self._on_washer_snapshot)
        # odśwież AC i boiler, oceń online
        for room in self._climate.online_map():
            try:
                await self._read_device("ac", room)
            except Exception:
                print("Not working climate refresh")
        try:
            await self._read_device("boiler", "boiler")
            self._boiler_online = True
            self.boilerOnlineChanged.emit(True)
        except Exception as exc:
            self._boiler_online = False
            self.boilerOnlineChanged.emit(False)
            print(f"Not working boiler refresh: {exc}")

        # Odśwież grzejniki jeśli są dostępne
        if self._heater:
            try:
                for room in self._heater.online_map():
                    try:
                        await self._read_device("heater", room)
                    except Exception:
                        print("Not working heater refresh")

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
            for room in online:
                self.deviceStaleChanged.emit("ac", room, self._device_stale.get(("ac", room), False))
            self.deviceStaleChanged.emit("boiler", "boiler", self._device_stale.get(("boiler", "boiler"), False))
            if self._heater:
                for room in self._heater.online_map():
                    self.deviceStaleChanged.emit("heater", room, self._device_stale.get(("heater", room), False))
            # brak API na online boilera? spróbuj z refresh – błąd emituj False
            self.ready.emit(True)
        except Exception as e:
            print(f"Error during init_all: {e}")

    @asyncSlot()
    async def refresh_connection(self):
        if self._shutdown_started:
            return
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = self.register_task(asyncio.create_task(self.init_all()))
        await asyncio.shield(self._refresh_task)

    # --- AC
    @asyncSlot(str)
    @device_operation("ac")
    async def turn_on_ac(self, room: str): await self._climate.turn_on(room)

    @asyncSlot(str)
    @device_operation("ac")
    async def turn_off_ac(self, room: str): await self._climate.turn_off(room)

    @asyncSlot(str)
    async def get_temp_indoor(self, room: str):
        self.tempIndoorChanged.emit(room, self._climate.temp_indoor(room))

    @asyncSlot(str)
    async def get_target_temp(self, room: str):
        self.targetTemperatureReceived.emit(room, self._climate.target_temp(room))

    @asyncSlot(str, float)
    @device_operation("ac")
    async def set_target_temp(self, room: str, temp: float):
        await self._climate.set_target_temp(room, temp)
        self.targetTemperatureReceived.emit(room, self._climate.target_temp(room))

    @asyncSlot(str)
    async def get_economy(self, room: str):
        self.economyReceived.emit(room, self._climate.economy(room))

    @asyncSlot(str, str)
    @device_operation("ac")
    async def set_economy(self, room: str, mode: str):
        await self._climate.set_economy(room, mode)
        self.economyReceived.emit(room, self._climate.economy(room))

    @asyncSlot(str)
    async def get_powerful(self, room: str):
        self.powerfulReceived.emit(room, self._climate.powerful(room))

    @asyncSlot(str, str)
    @device_operation("ac")
    async def set_powerful(self, room: str, mode: str):
        await self._climate.set_powerful(room, mode)
        self.powerfulReceived.emit(room, self._climate.powerful(room))

    @asyncSlot(str)
    async def get_low_noise(self, room: str):
        self.lowNoiseReceived.emit(room, self._climate.low_noise(room))

    @asyncSlot(str, str)
    @device_operation("ac")
    async def set_low_noise(self, room: str, mode: str):
        print(f"Setting low noise for room: {room}, MODE: {mode}")
        await self._climate.set_low_noise(room, mode)
        self.lowNoiseReceived.emit(room, self._climate.low_noise(room))

    @asyncSlot(str)
    async def get_mode_operation(self, room: str):
        print(f"Getting mode for room: {room}, MODE: {self._climate.operating_mode(room)}")
        self.modeReceived.emit(room, self._climate.operating_mode(room))

    @asyncSlot(str, str)
    @device_operation("ac")
    async def set_mode_operation(self, room: str, mode: str):
        await self._climate.set_operating_mode(room, mode)
        self.modeReceived.emit(room, self._climate.operating_mode(room))

    # --- Boiler
    @asyncSlot(str)
    @device_operation("boiler")
    async def set_water_heater_mode(self, mode: str):
        await self._boiler.set_mode(mode)
        await self._refresh_device_state("boiler", "boiler")
        self.modeOperating.emit(self._boiler.get_mode())

    @asyncSlot(float, str)
    @device_operation("boiler", "boilerSettingsFinished")
    async def apply_water_heater_settings(self, temp: float, mode: str):
        async with self._command_lock("boiler", "boiler"):
            try:
                self._validate_temperature(temp, 40, 65)
                if mode not in {"GREEN", "IMEMORY", "BOOST", "PROGRAM"}:
                    raise ValueError("Invalid boiler mode")
                await self._boiler.set_mode(mode)
                await self._boiler.set_target_temp(temp)
                await self._refresh_device_state("boiler", "boiler")
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
    @device_operation("boiler")
    async def set_water_heater_power(self, power: bool):
        await self._boiler.set_power(power)

    @asyncSlot()
    async def get_water_heater_power(self):
        self.powerStatus.emit(self._boiler.get_power())

    @asyncSlot(float)
    @device_operation("boiler")
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
    @device_operation("heater")
    async def turn_on_heater(self, room: str):
        """Włącz grzejnik w danym pokoju"""
        if self._heater:
            await self._heater.turn_on(room)
            self.heaterPowerChanged.emit(room, True)

    @asyncSlot(str)
    @device_operation("heater")
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
    @device_operation("heater")
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
    @device_operation("heater")
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
                        airflow=self._climate.airflow(room),
                        airflow_options=self._climate.airflow_options(room),
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

    @asyncSlot(str, float, str, bool, bool, bool, str, str)
    @device_operation("ac", "acSettingsFinished")
    async def apply_ac_settings(self, room, temp, mode, economy, powerful, quiet, fan_speed="", airflow=""):
        async with self._command_lock("ac", room):
            try:
                self._require_ac_on(room)
                if mode not in {"OFF", "FAN"}:
                    self._validate_temperature(temp, 10, 30)
                if fan_speed and fan_speed not in {"QUIET", "LOW", "MEDIUM", "HIGH", "AUTO"}:
                    raise ValueError("Invalid fan speed")
                if mode not in {"COOL", "HEAT", "FAN", "DRY", "AUTO", "OFF"}:
                    raise ValueError("Invalid mode")
                # Check external changes since the form was opened before
                # allowing the first write. A read error also blocks writes.
                await self._refresh_device_state("ac", room)
                self._require_ac_on(room)
                if airflow and mode != "OFF" and airflow not in self._climate.airflow_options(room):
                    raise ValueError("Unsupported airflow")
                if mode == "OFF":
                    await self._climate.turn_off(room)
                else:
                    await self._climate.set_operating_mode(room, mode)
                    if mode != "FAN":
                        await self._climate.set_target_temp(room, temp)
                    if fan_speed:
                        await self._climate.set_fan_speed(room, fan_speed)
                    if airflow:
                        await self._climate.set_airflow(room, airflow)
                    if self._climate.economy(room) is not None:
                        await self._climate.set_economy(room, "ON" if economy and not powerful else "OFF")
                    if self._climate.powerful(room) is not None:
                        await self._climate.set_powerful(room, "ON" if powerful else "OFF")
                    if self._climate.low_noise(room) is not None:
                        await self._climate.set_low_noise(room, "ON" if quiet else "OFF")
                    await self._climate.turn_on(room)
                await self._refresh_device_state("ac", room)
                self.acFanSpeedReceived.emit(room, self._climate.fan_speed(room))
                self.acAirflowReceived.emit(room, self._climate.airflow(room))
                if airflow and mode != "OFF" and self._climate.airflow(room) != airflow:
                    raise RuntimeError("Airflow was not confirmed by readback")
                await self.publish_dashboard()
            except ACSettingsBlocked:
                self.acSettingsFinished.emit(room, False, "Klimatyzator jest wyłączony lub jego stan nie jest potwierdzony. Włącz go przełącznikiem i odśwież odczyt.")
            except ValueError:
                self.acSettingsFinished.emit(room, False, "Nieprawidłowe ustawienia klimatyzatora.")
            except Exception:
                self.acSettingsFinished.emit(room, False, "Nie udało się zapisać lub odczytać wszystkich ustawień. Odśwież stan urządzenia.")
            else:
                self.acSettingsFinished.emit(room, True, "Wysłano ustawienia i odświeżono odczyt. Chmura może potwierdzić zmianę z opóźnieniem.")

    def _require_ac_on(self, room):
        if self._climate.operating_mode(room) not in {"COOL", "HEAT", "FAN", "DRY", "AUTO"}:
            raise ACSettingsBlocked()

    @asyncSlot(str, float, str, int)
    @device_operation("heater", "heaterSettingsFinished")
    async def apply_heater_settings(self, room, temp, mode, duration):
        async with self._command_lock("heater", room):
            try:
                self._validate_temperature(temp, 7, 28)
                if not self._heater or mode not in {"manual", "program"} or duration not in {30, 60, 120, 240}:
                    raise ValueError("Invalid heater settings")
                await self._heater.set_mode(room, mode)
                await self._heater.set_target_temp(room, temp, duration)
                await self._refresh_device_state("heater", room)
                await self.publish_dashboard()
            except Exception:
                self.heaterSettingsFinished.emit(room, False, "Nie udało się zapisać lub odczytać wszystkich ustawień. Odśwież stan urządzenia.")
            else:
                self.heaterSettingsFinished.emit(room, True, "Wysłano ustawienia i odświeżono odczyt. Chmura może potwierdzić zmianę z opóźnieniem.")

    @asyncSlot(str, str, bool)
    @device_operation(finished="devicePowerFinished")
    async def apply_device_power(self, kind, room, on):
        async with self._command_lock(kind, room):
            try:
                if kind == "ac":
                    await (self._climate.turn_on(room) if on else self._climate.turn_off(room))
                    await confirm_ac_power(self._climate, room, on)
                    self._set_device_stale(kind, room, False)
                elif kind == "boiler":
                    await self._boiler.set_power(on)
                    await self._refresh_device_state(kind, room)
                elif kind == "heater" and self._heater:
                    await (self._heater.turn_on(room) if on else self._heater.turn_off(room))
                    await self._refresh_device_state(kind, room)
                else:
                    raise ValueError("Device unavailable")
            except Exception:
                self._set_device_stale(kind, room, True)
                self.devicePowerFinished.emit(kind, room, False, "Błąd polecenia lub odczytu. Odśwież urządzenie.")
            else:
                self.devicePowerFinished.emit(kind, room, True, "Wysłano polecenie i odświeżono odczyt.")
            finally:
                await self.publish_dashboard()
