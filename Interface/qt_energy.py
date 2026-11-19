import asyncio
from datetime import timedelta
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer
from App.energy_service import EnergyService, month_shift


class EnergyController(QObject):
    changed = Signal()

    def __init__(self, service=None, parent=None):
        super().__init__(parent)
        self.service = service or EnergyService()
        self.mode = "hour"
        self.selected = self.service.clock().date() - timedelta(days=1)
        self._busy = False
        self._message = ""
        self._task = None
        self._closed = False
        self._timer = QTimer(self)
        self._timer.setInterval(60000)
        self._timer.timeout.connect(self.tick)

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(str, notify=changed)
    def message(self):
        return self._message

    @Property(str, notify=changed)
    def updated(self):
        return self.service.updated.strftime("%d.%m.%Y %H:%M") if self.service.updated else "jeszcze nie pobrano"

    @Property(str, notify=changed)
    def period(self):
        if self.mode == "hour":
            return self.selected.strftime("%d.%m.%Y")
        if self.mode == "day":
            return self.selected.strftime("%m.%Y")
        return str(self.selected.year)

    @Property('QVariantList', notify=changed)
    def rows(self):
        return self.service.series(self.mode, self.selected)

    @Property(str, notify=changed)
    def total(self):
        rows = self.rows
        values = [r['value'] for r in rows if r['value'] is not None]
        if not values:
            return "Brak danych"
        suffix = " (dostępne odczyty)" if not all(r['complete'] for r in rows) else ""
        return f"{sum(values):.2f} kWh".replace('.', ',') + suffix

    @Property(float, notify=changed)
    def maximum(self):
        return max([r['value'] or 0 for r in self.rows] + [0.001])

    @Property(bool, notify=changed)
    def canNext(self):
        return self._key(self.selected) < self._key(self.service.clock().date() - timedelta(days=1))

    @Property(bool, notify=changed)
    def canPrevious(self):
        earliest = month_shift(self.service.clock().date() - timedelta(days=1), -11)
        return self._key(self.selected) > self._key(earliest)

    def _key(self, day):
        return day.isoformat()[:{"hour": 10, "day": 7, "month": 4}[self.mode]]

    @Slot(str)
    def setMode(self, mode):
        if mode in ("hour", "day", "month"):
            self.mode = mode
            self.changed.emit()

    @Slot(int)
    def move(self, direction):
        if direction not in (-1, 1) or (direction > 0 and not self.canNext) or (direction < 0 and not self.canPrevious):
            return
        if self.mode == "hour":
            selected = self.selected + timedelta(days=direction)
        else:
            selected = month_shift(self.selected, direction * (12 if self.mode == "month" else 1))
        end = self.service.clock().date() - timedelta(days=1)
        self.selected = max(month_shift(end, -11), min(end, selected))
        self.changed.emit()

    @Slot()
    def refresh(self):
        if self._closed or self._busy:
            return
        if not self.service.adapter:
            self._message = "Brak konfiguracji eLicznik. Uzupełnij dane konta Tauron."
            self.changed.emit()
            return
        self._busy = True
        self._message = "Pobieranie historii z Taurona…"
        self.changed.emit()
        self._task = asyncio.create_task(self._refresh())

    async def _refresh(self):
        try:
            await self.service.refresh()
            self._message = "Pobrano historię. Dane Taurona mogą pojawiać się z opóźnieniem."
        except Exception:
            # Never emit remote exception text: it can contain account details.
            self._message = "Nie udało się pobrać danych. Sprawdź konto i internet. Zachowano ostatnie odczyty."
        finally:
            self._busy = False
            self.changed.emit()

    @Slot()
    def opened(self):
        if not self.service.readings:
            self.refresh()

    def start(self):
        self._timer.start()
        self.tick()

    def tick(self):
        if self.service.due():
            self.refresh()

    async def aclose(self):
        self._closed = True
        self._timer.stop()
        if self._task:
            await asyncio.gather(self._task, return_exceptions=True)
        await self.service.aclose()
