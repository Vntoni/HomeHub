import asyncio
from datetime import date, datetime, timedelta
from unittest.mock import Mock

import pytest

from App.energy_service import EnergyService, WARSAW, expected_hours, month_shift
from Adapters.elicznik_adapter import parse_consumption
from Interface.qt_energy import EnergyController


def clock():
    return datetime(2026, 11, 19, 12, 0, tzinfo=WARSAW)


def test_csv_consumption_and_repeated_hour():
    lines = ['Data;Rodzaj; Wartość ',
             '2026-10-25 03:00;pobór [kWh];0,3',
             '2026-10-25 03:00;pobór [kWh];0,4',
             '2026-10-25 03:00;oddanie [kWh];9,0']
    rows = parse_consumption(lines, date(2026, 10, 25), date(2026, 10, 25))
    assert len(rows) == 2 and sum(r[1] for r in rows) == pytest.approx(.7)
    service = EnergyService(clock=clock)
    service.readings = rows
    hourly = service.series('hour', date(2026, 10, 25))[2]
    assert hourly['value'] == .7 and hourly['complete']
    assert expected_hours(date(2026, 10, 25)) == 25
    assert expected_hours(date(2026, 3, 29)) == 23
    assert len(service.series('hour', date(2026, 3, 29))) == 23


def test_missing_is_not_zero_and_aggregation():
    service = EnergyService(clock=clock)
    service.readings = [['2026-11-18T00:00:00', 0], ['2026-11-18T01:00:00', 1.2], ['2026-11-17T00:00:00', 2.3]]
    hourly = service.series('hour', date(2026, 11, 18))
    assert hourly[0]['value'] == 0 and hourly[0]['complete']
    assert hourly[2]['value'] is None and not hourly[2]['complete']
    daily = service.series('day', date(2026, 11, 18))
    assert len(daily) == 18 and daily[-1]['value'] == 1.2
    monthly = service.series('month', date(2026, 11, 18))
    assert monthly[-1]['value'] == 3.5 and not monthly[-1]['complete']
    assert month_shift(date(2026, 1, 31), -1) == date(2025, 12, 1)


def test_noon_schedule_retry_and_restart(tmp_path):
    now = [clock().replace(hour=11)]
    service = EnergyService(Mock(), tmp_path/'energy.json', lambda: now[0])
    assert not service.due()
    now[0] = clock()
    assert service.due()
    service.last_attempt = now[0]
    assert not service.due()
    now[0] += timedelta(minutes=30)
    assert service.due()
    service.updated = clock()
    assert not service.due()
    service._save([], service.updated)
    restored = EnergyService(Mock(), service.cache, lambda: now[0])
    assert not restored.due()
    now[0] += timedelta(days=1)
    assert restored.due()


async def test_refresh_persists_and_failure_keeps_cache(tmp_path):
    adapter = Mock()
    adapter.fetch.return_value = [['2026-11-18T00:00:00', 1.5]]
    service = EnergyService(adapter, tmp_path/'energy.json', clock)
    await service.refresh()
    adapter.fetch.assert_called_once_with(date(2025, 12, 1), date(2026, 11, 18))
    before = service.cache.read_text()
    adapter.fetch.side_effect = RuntimeError('private remote error')
    with pytest.raises(RuntimeError):
        await service.refresh()
    assert service.cache.read_text() == before
    assert service.readings[0][1] == 1.5
    restored = EnergyService(adapter, service.cache, clock)
    assert restored.readings == service.readings
    await service.aclose()


async def test_coalesces_fetch_and_drains_on_shutdown():
    import threading
    entered, release = threading.Event(), threading.Event()
    calls = []
    def fetch(*args):
        calls.append(args)
        entered.set()
        release.wait(3)
        return [['2026-11-18T00:00:00', 2]]
    service = EnergyService(Mock(fetch=fetch), clock=clock)
    one = asyncio.create_task(service.refresh())
    while not entered.is_set():
        await asyncio.sleep(.01)
    two = asyncio.create_task(service.refresh())
    await asyncio.sleep(.01)
    closing = asyncio.create_task(service.aclose())
    await asyncio.sleep(.01)
    assert not closing.done()
    release.set()
    await asyncio.gather(one, two, closing)
    assert len(calls) == 1
    assert not await service.refresh()


async def test_controller_failure_no_secret_and_navigation():
    adapter = Mock()
    adapter.fetch.side_effect = RuntimeError('secret-password')
    controller = EnergyController(EnergyService(adapter, clock=clock))
    controller.refresh()
    controller.refresh()
    await controller._task
    assert not controller.busy and 'secret' not in controller.message
    assert adapter.fetch.call_count == 1
    assert not controller.canNext
    controller.move(-1)
    assert controller.canNext and controller.period == '17.11.2026'
    controller.setMode('day')
    controller.move(-1)
    assert controller.period == '10.2026'
    await controller.aclose()


def test_corrupt_cache_and_invalid_csv(tmp_path):
    path = tmp_path/'energy.json'
    path.write_text('{broken')
    assert EnergyService(cache=path).readings == []
    with pytest.raises(ValueError):
        parse_consumption(['<html>login</html>'], date.today(), date.today())


def test_login_uses_timeouts_and_closes_session(monkeypatch):
    from Adapters.elicznik_adapter import ELicznikAdapter, EnergyLoginError
    session = Mock()
    form = Mock(text='<form id="kc-form-login" action="https://login.tauron-dystrybucja.pl/auth">')
    rejected = Mock(text='<form id="kc-form-login">')
    # Session.get/post normally delegate to request; model that contract.
    session.request.side_effect = [form, rejected]
    session.get.side_effect = lambda url, **kw: session.request('GET', url, **kw)
    session.post.side_effect = lambda url, **kw: session.request('POST', url, **kw)
    monkeypatch.setattr('Adapters.elicznik_adapter.Session', lambda: session)
    original_request = session.request
    with pytest.raises(EnergyLoginError):
        ELicznikAdapter('test@example.invalid', 'test-only').fetch(date.today(), date.today())
    assert all(call.kwargs['timeout'] == (10, 40) for call in original_request.call_args_list)
    session.close.assert_called_once()


def test_login_never_posts_credentials_to_unexpected_host(monkeypatch):
    from Adapters.elicznik_adapter import TauronClient, EnergyLoginError
    session = Mock()
    session.get.return_value.text = '<form id="kc-form-login" action="https://example.invalid/auth">'
    monkeypatch.setattr('Adapters.elicznik_adapter.Session', lambda: session)
    with pytest.raises(EnergyLoginError):
        TauronClient('test@example.invalid', 'test-only').login()
    session.post.assert_not_called()
