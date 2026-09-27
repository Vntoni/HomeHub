"""In-memory demo services. No credentials, network, MQTT, BLE or database."""
from qasync import asyncSlot
from Interface.qt_backend import QtHomeBackend
from App.sensor_service import SensorService


class DemoClimate:
    def __init__(self):
        self.units = {room: dict(current=21.5, target=22.0, mode="HEAT",
                                power=True, economy=False, powerful=False, low_noise=False)
                      for room in ("Salon", "Jadalnia")}

    async def refresh_all(self): pass
    async def refresh(self, room): pass
    def online_map(self): return {room: True for room in self.units}
    def temp_indoor(self, room): return self.units[room]["current"]
    def target_temp(self, room): return self.units[room]["target"]
    def operating_mode(self, room): return self.units[room]["mode"]
    def economy(self, room): return self.units[room]["economy"]
    def powerful(self, room): return self.units[room]["powerful"]
    def low_noise(self, room): return self.units[room]["low_noise"]
    async def turn_on(self, room):
        self.units[room]["power"] = True
        if self.units[room]["mode"] == "OFF":
            self.units[room]["mode"] = "HEAT"
    async def turn_off(self, room):
        self.units[room]["power"] = False
        self.units[room]["mode"] = "OFF"
    async def set_target_temp(self, room, temp): self.units[room]["target"] = temp
    async def set_operating_mode(self, room, mode): self.units[room]["mode"] = mode
    async def set_economy(self, room, mode): self.units[room]["economy"] = mode == "ON"
    async def set_powerful(self, room, mode): self.units[room]["powerful"] = mode == "ON"
    async def set_low_noise(self, room, mode): self.units[room]["low_noise"] = mode == "ON"


class DemoBoiler:
    def __init__(self):
        self.power, self.target, self.current, self.mode = True, 55.0, 43.0, "GREEN"

    async def refresh(self): pass
    async def set_power(self, on): self.power = on
    def get_power(self): return self.power
    async def set_target_temp(self, temp): self.target = temp
    def get_target_temp(self): return self.target
    def get_current_temp(self): return self.current
    async def set_mode(self, mode): self.mode = mode
    def get_mode(self): return self.mode


class DemoHeaters:
    def __init__(self):
        self.units = {room: dict(current=20.5, target=21.0, mode="program", power=False)
                      for room in ("Juras", "Migacze", "Julia")}

    async def refresh_all(self): pass
    async def refresh(self, room): pass
    def online_map(self): return {room: True for room in self.units}
    def get_current_temp(self, room): return self.units[room]["current"]
    def get_target_temp(self, room): return self.units[room]["target"]
    def get_mode(self, room): return self.units[room]["mode"]
    def get_power(self, room): return self.units[room]["power"]
    async def turn_on(self, room): self.units[room]["power"] = True
    async def turn_off(self, room): self.units[room]["power"] = False
    async def set_mode(self, room, mode): self.units[room]["mode"] = mode
    async def set_target_temp(self, room, temp, duration_minutes=120):
        self.units[room]["target"] = temp


class DemoSensor:
    def get_temperature(self): return 21.5
    def get_humidity(self): return 48.0


class DemoBackend(QtHomeBackend):
    @asyncSlot()
    async def start_washer_monitor(self):
        self.washerOnlineChanged.emit(False)


async def build_demo_backend():
    return DemoBackend(DemoClimate(), DemoBoiler(), None, DemoHeaters(),
                         SensorService({room: DemoSensor()
                                        for room in ("salon", "jadalnia", "lazienka")}))
