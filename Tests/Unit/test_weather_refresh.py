import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from Adapters.open_meteo_adapter import OpenMeteoAdapter


@pytest.fixture
def fake_response(monkeypatch):
    calls = []
    result = {"current": {"temperature_2m": 12.5, "relative_humidity_2m": 65,
                          "wind_speed_10m": 3.0, "weather_code": 0}}
    async def get(client, url, **kwargs):
        calls.append(kwargs)
        if isinstance(result.get("error"), Exception):
            raise result["error"]
        return httpx.Response(result.get("status", 200), json=result,
                              request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    return result, calls


async def test_fake_http_success_maps_units_condition_and_timestamp(fake_response):
    data, calls = fake_response
    reading = await OpenMeteoAdapter(0, 0).fetch()
    assert reading is not None
    assert reading["temp_out"] == 12.5
    assert reading["humidity_out"] == 65
    assert reading["wind_speed"] == 3.0
    assert reading["condition"] == "bezchmurnie"
    assert reading["ts"].utcoffset().total_seconds() == 0
    assert calls[0]["params"]["wind_speed_unit"] == "ms"


@pytest.mark.parametrize("scenario", ["http_error", "timeout", "missing", "invalid_json"])
async def test_failed_response_returns_unavailable_without_writing(fake_response, scenario):
    data, calls = fake_response
    if scenario == "http_error":
        data["status"] = 503
    elif scenario == "timeout":
        data["error"] = httpx.ReadTimeout("fake timeout")
    elif scenario == "missing":
        data.clear()
    else:
        data["error"] = ValueError("fake JSON decode failure")
    repo = Mock(save_weather_reading=AsyncMock())
    assert await OpenMeteoAdapter(0, 0, repository=repo).fetch() is None
    assert calls, "The HTTP path must be exercised; a missing import is not success"
    repo.save_weather_reading.assert_not_awaited()


async def test_polling_saves_one_reading_and_can_be_cancelled():
    saved = asyncio.Event()
    async def save(**kwargs):
        saved.set()
    repo = Mock(save_weather_reading=AsyncMock(side_effect=save))
    adapter = OpenMeteoAdapter(0, 0, repository=repo, poll_interval_seconds=3600)
    reading = dict(temp_out=12.5, humidity_out=65, condition="bezchmurnie",
                   wind_speed=3.0, ts=datetime.now(timezone.utc))
    adapter.fetch = AsyncMock(return_value=reading)
    task = asyncio.create_task(adapter.start_polling())
    try:
        await asyncio.wait_for(saved.wait(), timeout=1)
        assert adapter.get_latest() == reading
        repo.save_weather_reading.assert_awaited_once_with(**reading)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


async def test_weather_reaches_dashboard_without_database_and_failure_keeps_last_reading():
    from Interface.qt_weather import WeatherController
    from PySide6.QtCore import QCoreApplication
    app = QCoreApplication.instance() or QCoreApplication([])
    controller = WeatherController()
    published = asyncio.Event()
    reading = dict(temp_out=-2.5, humidity_out=65, condition="śnieg",
                   wind_speed=3.0, weather_code=73, is_day=True,
                   ts=datetime.now(timezone.utc))
    def update(value):
        controller.update(value)
        published.set()
    adapter = OpenMeteoAdapter(0, 0, on_update=update)
    adapter.fetch = AsyncMock(return_value=reading)
    task = asyncio.create_task(adapter.start_polling())
    try:
        await asyncio.wait_for(published.wait(), 1)
        assert controller.temperature == '-2,5°C'
        assert controller.icon == 'snow'
        assert not controller.stale
        controller.update(None)
        assert controller.temperature == '-2,5°C'
        assert controller.stale
        assert controller.status == 'Ostatni odczyt'
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.parametrize('code,day,icon', [(0, True, 'sun'), (0, False, 'moon'),
    (2, True, 'partly'), (3, True, 'cloud'), (48, True, 'fog'),
    (67, True, 'rain'), (86, True, 'snow'), (99, True, 'storm'), (999, True, 'unknown')])
def test_weather_pictograms(code, day, icon):
    from Interface.qt_weather import weather_icon
    assert weather_icon(code, day) == icon


@pytest.mark.parametrize('value', [None, True, float('nan'), 'cold'])
async def test_invalid_temperature_is_unavailable(fake_response, value):
    data, _ = fake_response
    data['current']['temperature_2m'] = value
    assert await OpenMeteoAdapter(0, 0).fetch() is None
