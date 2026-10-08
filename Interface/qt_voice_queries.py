"""Receive dashboard signals on the Qt thread; expose no command methods."""
from PySide6.QtCore import QObject, Slot
from App.voice_queries import ReadOnlyHomeQueries


class VoiceQueryBridge(QObject):
    def __init__(self, backend):
        super().__init__(backend)
        self.cache = ReadOnlyHomeQueries()
        backend.sensorTempChanged.connect(self.temperature)
        backend.sensorHumidityChanged.connect(self.humidity)
        backend.tempIndoorChanged.connect(self.indoor)
        backend.modeReceived.connect(self.mode)
        backend.deviceStaleChanged.connect(self.stale)
        backend.acSalonOnlineChanged.connect(self.salon_online)
        backend.acJadalniaOnlineChanged.connect(self.jadalnia_online)

    @Slot(str, 'QVariant')
    def temperature(self, room, value): self.cache.sensor(room, 'temperature', value)

    @Slot(str, 'QVariant')
    def humidity(self, room, value): self.cache.sensor(room, 'humidity', value)

    @Slot(str, float)
    def indoor(self, room, value): self.cache.indoor(room, value)

    @Slot(str, str)
    def mode(self, room, value): self.cache.mode(room, value)

    @Slot(str, str, bool)
    def stale(self, kind, room, value): self.cache.stale(kind, room, value)

    @Slot(bool)
    def salon_online(self, online): self.cache.online('salon', online)

    @Slot(bool)
    def jadalnia_online(self, online): self.cache.online('jadalnia', online)

    def answer(self, text):
        return self.cache.answer(text)
