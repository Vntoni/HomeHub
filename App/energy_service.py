"""Persistent electricity readings and a Warsaw-noon refresh policy."""
import asyncio
import calendar
import json
import math
import os
from datetime import datetime, date, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")


def now_local():
    return datetime.now(WARSAW)


def month_shift(day, months):
    number = day.year * 12 + day.month - 1 + months
    return date(number // 12, number % 12 + 1, 1)


def expected_hours(day):
    start = datetime.combine(day, time(), WARSAW).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time(), WARSAW).astimezone(timezone.utc)
    return int((end - start).total_seconds() / 3600)


class EnergyService:
    def __init__(self, adapter=None, cache=None, clock=now_local):
        self.adapter, self.cache, self.clock = adapter, cache, clock
        self.readings = []
        self.updated = None
        self.last_attempt = None
        self.task = None
        self.closed = False
        if cache:
            try:
                data = json.loads(cache.read_text())
                rows = data["readings"]
                for stamp, value in rows:
                    datetime.fromisoformat(stamp)
                    if not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
                        raise ValueError("Invalid cache")
                updated = datetime.fromisoformat(data["updated"])
                if updated.tzinfo is None:
                    raise ValueError("Missing timezone")
                self.readings, self.updated = rows, updated
            except (OSError, ValueError, KeyError, TypeError):
                pass

    def due(self):
        if self.closed or not self.adapter:
            return False
        now = self.clock()
        if now.hour < 12:
            return False
        noon = now.replace(hour=12, minute=0, second=0, microsecond=0)
        if self.updated and self.updated >= noon:
            return False
        return not self.last_attempt or now - self.last_attempt >= timedelta(minutes=30)

    async def refresh(self):
        if self.closed:
            return False
        if self.task and not self.task.done():
            return await asyncio.shield(self.task)
        self.task = asyncio.create_task(self._refresh())
        return await asyncio.shield(self.task)

    async def _refresh(self):
        if not self.adapter:
            raise RuntimeError("Energy credentials missing")
        self.last_attempt = self.clock()
        end = self.clock().date() - timedelta(days=1)
        start = month_shift(end, -11)
        rows = await asyncio.to_thread(self.adapter.fetch, start, end)
        if not rows:
            raise ValueError("Empty energy response")
        updated = self.clock()
        if self.cache:
            # Write before replacing memory: failed downloads/writes retain the
            # previous successful snapshot, including after process restart.
            await asyncio.to_thread(self._save, rows, updated)
        self.readings, self.updated = rows, updated
        return True

    def _save(self, rows, updated):
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.cache.with_suffix(".tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump({"updated": updated.isoformat(), "readings": rows}, stream)
        temporary.replace(self.cache)

    async def aclose(self):
        self.closed = True
        if self.task:
            await asyncio.gather(self.task, return_exceptions=True)

    def series(self, mode, selected):
        end = self.clock().date() - timedelta(days=1)
        groups = {}
        for stamp, value in self.readings:
            day = date.fromisoformat(stamp[:10])
            if day > end:
                continue
            if mode == "hour" and day == selected:
                key = stamp[11:16]
            elif mode == "day" and (day.year, day.month) == (selected.year, selected.month):
                key = day.isoformat()
            elif mode == "month" and day.year == selected.year:
                key = stamp[:7]
            else:
                continue
            groups.setdefault(key, []).append(value)
        rows = []
        if mode == "hour":
            keys = [(f"{hour:02}:00", 1) for hour in range(24)]
            # The portal represents repeated local hours without an offset.
            if expected_hours(selected) == 23:
                keys = [(k, n) for k, n in keys if k != "02:00"]
            elif expected_hours(selected) == 25:
                keys = [(k, 2 if k == "02:00" else n) for k, n in keys]
        else:
            days = calendar.monthrange(selected.year, selected.month)[1]
            starts = ([date(selected.year, selected.month, d) for d in range(1, days + 1)]
                      if mode == "day" else [date(selected.year, m, 1) for m in range(1, 13)])
            keys = []
            for start in starts:
                if start > end:
                    continue
                finish = min(end, start if mode == "day" else month_shift(start, 1) - timedelta(days=1))
                hours = sum(expected_hours(start + timedelta(days=i)) for i in range((finish-start).days+1))
                keys.append((start.isoformat() if mode == "day" else start.strftime("%Y-%m"), hours))
        for key, expected in keys:
            values = groups.get(key, [])
            rows.append({"label": key + (" ×2" if mode == "hour" and expected == 2 else ""),
                         "value": round(sum(values), 3) if values else None,
                         "complete": len(values) == expected,
                         "count": len(values), "expected": expected})
        return rows


def production_energy():
    config = Path(os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "bazadomowa" / "energy.json"
    try:
        credentials = json.loads(config.read_text())
    except (OSError, ValueError):
        credentials = {}
    if not isinstance(credentials, dict):
        credentials = {}
    username = os.getenv("ELICZNIK_USERNAME") or credentials.get("username")
    password = os.getenv("ELICZNIK_PASSWORD") or credentials.get("password")
    adapter = None
    if username and password:
        from Adapters.elicznik_adapter import ELicznikAdapter
        adapter = ELicznikAdapter(username, password, os.getenv("ELICZNIK_SITE") or credentials.get("site"))
    cache = Path(os.getenv("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "bazadomowa" / "energy.json"
    return EnergyService(adapter, cache)


def demo_energy():
    class DemoAdapter:
        def fetch(self, start, end):
            rows = []
            day = start
            while day <= end:
                for hour in range(24):
                    if expected_hours(day) == 23 and hour == 2:
                        continue
                    repeats = 2 if expected_hours(day) == 25 and hour == 2 else 1
                    for _ in range(repeats):
                        rows.append([datetime.combine(day, time(hour)).isoformat(), round(0.12 + (hour % 7) * 0.06, 3)])
                day += timedelta(days=1)
            return rows
    service = EnergyService(DemoAdapter())
    end = service.clock().date() - timedelta(days=1)
    service.readings = service.adapter.fetch(month_shift(end, -11), end)
    service.updated = service.clock()
    return service
