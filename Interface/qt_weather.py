"""Live dashboard weather, independent of optional history storage."""
from datetime import datetime, timezone
from PySide6.QtCore import QObject, Signal, Property, QTimer


def weather_icon(code, is_day=True):
    if code == 0:
        return "sun" if is_day else "moon"
    if code in (1, 2):
        return "partly" if is_day else "cloud"
    if code == 3:
        return "cloud"
    if code in (45, 48):
        return "fog"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "storm"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    return "unknown"


class WeatherController(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._reading = None
        self._failed = False
        self._timer = QTimer(self)
        self._timer.setInterval(60000)
        self._timer.timeout.connect(self.changed.emit)
        self._timer.start()

    def update(self, reading):
        self._failed = reading is None
        if reading is not None:
            self._reading = reading
        self.changed.emit()

    @Property(str, notify=changed)
    def temperature(self):
        return f'{self._reading["temp_out"]:.1f}'.replace('.', ',') + '°C' if self._reading else '—°C'

    @Property(str, notify=changed)
    def icon(self):
        return weather_icon(self._reading.get('weather_code'), self._reading.get('is_day', True)) if self._reading else 'unknown'

    @Property(bool, notify=changed)
    def stale(self):
        return self._failed or bool(self._reading and (datetime.now(timezone.utc) - self._reading['ts']).total_seconds() > 7200)

    @Property(str, notify=changed)
    def status(self):
        if not self._reading:
            return 'Brak danych' if self._failed else 'Pobieranie…'
        return 'Ostatni odczyt' if self.stale else 'Na zewnątrz'

    @Property(str, notify=changed)
    def details(self):
        if not self._reading:
            return 'Pogoda chwilowo niedostępna.' if self._failed else 'Pobieranie pogody…'
        stamp = self._reading['ts'].astimezone().strftime('%d.%m %H:%M')
        return f'{self._reading["condition"]} · pobrano {stamp}' + (' · dane nieaktualne' if self.stale else '')
