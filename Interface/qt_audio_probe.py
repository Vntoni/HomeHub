"""User-triggered five-second diagnostic. No files, network, STT or commands."""
from array import array
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer


class AudioProbeController(QObject):
    changed = Signal()
    devicesChanged = Signal()
    MAX_SECONDS = 5
    MAX_BYTES = 4 * 1024 * 1024

    def __init__(self, factory=None, parent=None):
        super().__init__(parent)
        self._factory = factory
        self._adapter = None
        self._connected = self._opened = self._closed = False
        self._inputs, self._outputs = [], []
        self._state = "idle"
        self._message = "Test uruchomisz przyciskiem. Mikrofon teraz nie nagrywa."
        self._level = self._peak = 0.0
        self._pcm = bytearray()
        self._format = None
        self._generation = 0
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._deadline)

    @Property('QVariantList', notify=devicesChanged)
    def inputs(self): return self._inputs
    @Property('QVariantList', notify=devicesChanged)
    def outputs(self): return self._outputs
    @Property(str, notify=changed)
    def state(self): return self._state
    @Property(str, notify=changed)
    def message(self): return self._message
    @Property(float, notify=changed)
    def level(self): return self._level
    @Property(bool, notify=changed)
    def busy(self): return self._state in ("recording", "playing")
    @Property(bool, notify=changed)
    def hasRecording(self): return bool(self._pcm) and self._format is not None

    def set_connected(self, connected):
        if self._closed or connected == self._connected:
            return
        self._connected = connected
        if not connected:
            self.clear()
            self._inputs, self._outputs = [], []
            self.devicesChanged.emit()
            self._message = "ReSpeaker odłączony. Próbka została usunięta."
            self.changed.emit()
        elif self._opened:
            self.refresh()

    @Slot()
    def openPanel(self):
        if not self._closed:
            self._opened = True
            self.refresh()

    @Slot()
    def refresh(self):
        if self._closed or not self._opened or self.busy:
            return
        self._inputs, self._outputs = [], []
        try:
            if not self._connected:
                self._message = "Podłącz ReSpeaker przez USB."
            elif self._factory is None:
                self._message = "Audio sprzętowe jest wyłączone w trybie demo."
            else:
                if self._adapter is None:
                    self._adapter = self._factory(self._devices_changed)
                self._inputs, self._outputs = self._adapter.devices()
                self._message = ("Wybierz mikrofon i naciśnij Nagraj 5 s."
                                 if self._inputs else "USB wykryte, ale brak wejścia audio ReSpeaker. Sprawdź systemowe urządzenia dźwiękowe.")
            self._state = "idle"
        except Exception:
            self._state = "error"
            self._message = "Nie można odczytać urządzeń audio. Pozostałe funkcje HomeHub działają."
        self.devicesChanged.emit()
        self.changed.emit()

    def _devices_changed(self):
        if self._closed or not self._opened:
            return
        self.clear()
        self.refresh()
        self._message = "Lista urządzeń audio zmieniła się. Wybierz urządzenie ponownie."
        self.changed.emit()

    def _stop_transport(self):
        self._generation += 1  # Ignore callbacks already queued before stop.
        self._timer.stop()
        if self._adapter is not None:
            self._adapter.stop()
        self._level = 0.0

    def _fail(self, generation):
        if generation != self._generation or self._closed:
            return
        self.clear()
        self._state = "error"
        self._message = "Test audio nie powiódł się. Sprawdź połączenie, wybrane urządzenie i czy nie jest zajęte."
        self.changed.emit()

    @Slot(str)
    def record(self, device_id):
        if self._closed or not self._opened or not self._connected or self.busy:
            return
        self.clear()
        if self._adapter is None or device_id not in {d['id'] for d in self._inputs}:
            self._message = "Wybierz dostępny mikrofon ReSpeaker."
            self.changed.emit()
            return
        generation = self._generation
        self._state, self._message = "recording", "Nagrywanie — powiedz kilka słów (maks. 5 s)."
        self.changed.emit()
        try:
            fmt = self._adapter.record(device_id, lambda data: self._data(generation, data),
                                       lambda: self._fail(generation))
            if generation != self._generation:
                return
            if not (8000 <= fmt.rate <= 96000 and 1 <= fmt.channels <= 4
                    and fmt.bytes_per_second * self.MAX_SECONDS <= self.MAX_BYTES):
                raise ValueError("Unsupported bounded PCM format")
            self._format = fmt
            self._timer.start(self.MAX_SECONDS * 1000)
        except Exception:
            self._fail(generation)

    def _data(self, generation, data):
        if generation != self._generation or self._state != "recording" or self._format is None:
            return
        limit = self._format.bytes_per_second * self.MAX_SECONDS
        part = data[:max(0, limit - len(self._pcm))]
        self._pcm.extend(part)
        samples = array('h')
        samples.frombytes(part[:len(part) // 2 * 2])
        self._level = max((abs(v) / 32768 for v in samples), default=0.0)
        self._peak = max(self._peak, self._level)
        self.changed.emit()
        if len(self._pcm) >= limit:
            self.stop()

    def _deadline(self):
        if self._state == "recording":
            self.stop()
        elif self._state == "playing":
            self._fail(self._generation)

    @Slot()
    def stop(self):
        was_recording = self._state == "recording"
        self._stop_transport()
        self._state = "idle"
        if was_recording:
            if self._format:
                self._pcm = self._pcm[:len(self._pcm) // self._format.frame_bytes * self._format.frame_bytes]
            self._message = ("Brak próbek audio. Sprawdź mikrofon." if not self._pcm else
                             "Próbka gotowa. Sygnał jest bardzo cichy — sprawdź przycisk Mute." if self._peak < .001 else
                             "Próbka gotowa. Możesz ją odsłuchać.")
        else:
            self._message = "Odtwarzanie zakończone."
        self.changed.emit()

    @Slot(str)
    def play(self, device_id):
        if self._closed or not self._opened or not self._connected or self.busy or not self.hasRecording:
            return
        if device_id not in {d['id'] for d in self._outputs}:
            self._message = "Wybierz wyjście dźwięku."
            self.changed.emit()
            return
        self._generation += 1
        generation = self._generation
        self._state, self._message = "playing", "Odtwarzanie próbki — mikrofon nie nagrywa."
        self._timer.start((self.MAX_SECONDS + 2) * 1000)
        self.changed.emit()
        try:
            self._adapter.play(device_id, bytes(self._pcm), self._format,
                               lambda: self.stop() if generation == self._generation else None,
                               lambda: self._fail(generation))
        except Exception:
            self._fail(generation)

    @Slot()
    def clear(self):
        self._stop_transport()
        self._pcm.clear()
        self._format = None
        self._peak = 0.0
        self._state = "idle"
        self._message = "Próbka usunięta. Mikrofon nie nagrywa."
        self.changed.emit()

    @Slot()
    def closePanel(self):
        self._opened = False
        self.clear()

    def shutdown(self):
        if self._closed:
            return
        self._closed = True
        self.closePanel()
        if self._adapter is not None:
            self._adapter.close()
            self._adapter = None
