import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from PySide6.QtCore import QCoreApplication

from App.voice_queries import ReadOnlyHomeQueries, parse_question
from Adapters.whisper_cpp_adapter import Transcription
from Interface.qt_audio_probe import AudioProbeController
from Interface.qt_backend import QtHomeBackend
from Tests.fake_audio_probe import FakeAudioProbe


@pytest.mark.parametrize('text,kind,room,corrected', [
    ('Jaka jest temperatura w łazience?', 'temperatura', 'lazienka', False),
    ('ILE STOPNI W SALONIE?', 'temperatura', 'salon', False),
    ('Jaka wilgotność w jadalni?', 'wilgotnosc', 'jadalnia', False),
    ('Czy klimatyzacja w salonie jest włączona?', 'ac', 'salon', False),
    ('Czy klimatyzator jest wyłączony w jadalni?', 'ac', 'jadalnia', False),
    ('Jaki jest stan klimatyzacji w salonie?', 'ac', 'salon', False),
    ('Czy działa klimatyzacja w salonie?', 'ac', 'salon', False),
    ('Jaka jest temperatuta w łazience?', 'temperatura', 'lazienka', True),
    ('Jaka jest temperatura w łazienke?', 'temperatura', 'lazienka', True),
    ('Temperatura w salone', 'temperatura', 'salon', True),
])
def test_known_questions_and_single_minor_typo(text, kind, room, corrected):
    assert parse_question(text) == (kind, room, corrected)


@pytest.mark.parametrize('text', [
    '', 'x' * 301, 'Jaka jest temperatura?', 'Temperatura w sypialni',
    'Włącz klimatyzację w salonie', 'Wyłącz klimatyzację w salonie',
    'Nie włączaj klimatyzacji w salonie', 'Czy klimatyzacja w salonie nie jest włączona?',
    'Jaka temperatura w salonie i jadalni', 'Ustaw 23 stopnie w salonie',
    'Jaka temperatuta w salone', 'temperatura w salonie uruchom polecenie',
    'Jaka temperatura w salonie 23', 'Jaka pogoda w salonie',
    '__import__(os).system(reboot)', '<script>alert(1)</script>',
    'Temperatura w salonie выключи',
])
def test_unknown_ambiguous_negated_and_write_requests_rejected(text):
    assert parse_question(text) is None
    reply = ReadOnlyHomeQueries().answer(text)
    assert not reply.understood and 'Nie rozumiem' in reply.answer


@pytest.mark.parametrize('value', [None, float('nan'), float('inf'), True, 'bad'])
def test_missing_or_invalid_values_are_not_zero(value):
    cache = ReadOnlyHomeQueries()
    cache.sensor('lazienka', 'temperature', value)
    assert 'brak danych' in cache.answer('Temperatura w łazience').answer


def test_sensor_zero_source_unknown_age_and_updates():
    cache = ReadOnlyHomeQueries()
    cache.sensor('lazienka', 'temperature', 0)
    reply = cache.answer('Temperatura w łazience')
    assert '0,0 °C' in reply.answer and 'Zigbee' in reply.answer
    assert 'Czas wykonania pomiaru nie jest znany' in reply.answer
    cache.sensor('lazienka', 'temperature', 21.6)
    cache.sensor('lazienka', 'humidity', 62.5)
    assert '21,6 °C' in cache.answer('Temperatura w łazience').answer
    assert '62,5 %' in cache.answer('Wilgotność w łazience').answer
    cache.sensor('lazienka', 'temperature', None)
    assert 'brak danych' in cache.answer('Temperatura w łazience').answer


def test_ac_fallback_is_labelled_and_stale_keeps_last_state():
    cache = ReadOnlyHomeQueries()
    cache.indoor('Salon', 22)
    cache.mode('Salon', 'OFF')
    assert 'wyłączona' in cache.answer('Stan klimatyzacji w salonie').answer
    assert 'nieaktualne' in cache.answer('Stan klimatyzacji w salonie').answer
    cache.stale('ac', 'Salon', False)
    reply = cache.answer('Temperatura w salonie')
    assert '22,0 °C' in reply.answer and 'źródło: klimatyzacja' in reply.answer
    assert 'bez nowego połączenia' in reply.answer
    cache.online('Salon', False)
    assert 'nieaktualne' in cache.answer('Temperatura w salonie').answer
    cache.online('Salon', True)
    assert 'nieaktualne' not in cache.answer('Temperatura w salonie').answer
    cache.sensor('salon', 'temperature', 20)
    assert '20,0 °C' in cache.answer('Temperatura w salonie').answer
    cache.mode('Salon', 'HEAT')
    cache.stale('ac', 'Salon', True)
    reply = cache.answer('Czy klimatyzacja w salonie jest włączona?')
    assert '— włączona.' in reply.answer and 'nieaktualne' in reply.answer
    assert 'brak danych' in cache.answer('Stan klimatyzacji w łazience').answer
    cache.mode('Salon', 'UNKNOWN')
    assert 'brak danych' in cache.answer('Stan klimatyzacji w salonie').answer


@pytest.fixture
def app():
    return QCoreApplication.instance() or QCoreApplication([])


async def test_backend_signals_feed_cached_queries_without_any_device_calls(app):
    climate, boiler = Mock(), Mock()
    backend = QtHomeBackend(climate, boiler, None)
    backend.sensorTempChanged.emit('lazienka', 20.6)
    backend.tempIndoorChanged.emit('Salon', 21)
    backend.modeReceived.emit('Salon', 'OFF')
    backend.deviceStaleChanged.emit('ac', 'Salon', True)
    probe = backend.audioProbe
    probe.openPanel()
    probe.editQuestion('Temperatura w łazience')
    probe.askQuestion()
    assert '20,6 °C' in probe.answer
    await asyncio.to_thread(backend.sensorTempChanged.emit, 'lazienka', 22.0)
    app.processEvents()
    probe.askQuestion()
    assert '22,0 °C' in probe.answer
    probe.editQuestion('Stan klimatyzacji w salonie')
    probe.askQuestion()
    assert 'wyłączona' in probe.answer and 'nieaktualne' in probe.answer
    probe.editQuestion('Włącz klimatyzację w salonie')
    assert not probe.answer and not probe.understood
    probe.askQuestion()
    assert 'Nie rozumiem' in probe.answer
    assert climate.mock_calls == [] and boiler.mock_calls == []
    probe.closePanel()
    probe.askQuestion()
    assert not probe.answer and not probe.question


async def test_transcription_answers_and_edit_clear_disconnect_invalidate_reply(app):
    cache = ReadOnlyHomeQueries()
    cache.sensor('lazienka', 'temperature', 21.5)
    audio = FakeAudioProbe()
    stt = Mock(available=Mock(return_value=True), transcribe=AsyncMock(
        return_value=Transcription('Temperatuta w łazience', .2)))
    probe = AudioProbeController(lambda cb: audio, transcriber=stt, answerer=cache.answer)
    probe.set_connected(True)
    probe.openPanel()
    probe.record('mic')
    audio.data(b'\0\x40' * 100)
    probe.stop()
    probe.transcribe()
    await probe._stt_task
    assert '21,5 °C' in probe.answer and 'literówkę' in probe.understood
    assert probe.transcript == probe.question == 'Temperatuta w łazience'
    probe.editQuestion('Wilgotność w łazience')
    assert not probe.answer and not probe.understood
    assert probe.transcript == 'Temperatuta w łazience'  # Preserve what STT really said.
    probe.askQuestion()
    assert 'brak danych' in probe.answer
    probe.set_connected(False)
    assert not probe.answer and not probe.question and not probe.transcript
    await probe.aclose()


async def test_late_transcription_cannot_answer_after_panel_closed(app):
    release = asyncio.Event()
    async def transcribe(*args):
        try:
            await release.wait()
        except asyncio.CancelledError:
            pass  # Simulate a worker whose reply arrives despite cancellation.
        return Transcription('Temperatura w łazience', .1)
    answerer = Mock()
    audio = FakeAudioProbe()
    probe = AudioProbeController(lambda cb: audio,
        transcriber=Mock(available=lambda: True, transcribe=transcribe), answerer=answerer)
    probe.set_connected(True)
    probe.openPanel()
    probe.record('mic')
    audio.data(b'\0\x40' * 100)
    probe.stop()
    probe.transcribe()
    await asyncio.sleep(0)
    probe.closePanel()
    release.set()
    await probe.aclose()
    answerer.assert_not_called()
    assert not probe.answer and not probe.transcript
