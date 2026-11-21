import asyncio
from array import array
from unittest.mock import AsyncMock, Mock

import pytest
from PySide6.QtCore import QCoreApplication

from App.voice_activity import UtteranceBuffer, is_toggle
from App.pcm_conversion import resample_pcm
from App.voice_queries import Reply
from Adapters.whisper_cpp_adapter import Transcription, wav_bytes
from Interface.qt_conversation import ConversationController
from Interface.qt_audio_probe import AudioProbeController
from Ports.audio_probe import PcmFormat
from Tests.fake_audio_probe import FakeAudioProbe


@pytest.mark.parametrize('text', ['Klopsy', 'KLOPSY!', 'Klopsy.', '  klopsy  '])
def test_toggle_phrase(text):
    assert is_toggle(text)


@pytest.mark.parametrize('text', ['', 'gaga', 'Google gaga', 'Powiedz klopsy', 'klopsy jaka temperatura', None])
def test_other_words_do_not_toggle(text):
    assert not is_toggle(text)


def test_vad_silence_preroll_partial_frames_and_bound():
    fmt = PcmFormat(16000, 1)
    vad = UtteranceBuffer(fmt)
    for _ in range(100):
        assert vad.feed(b'\0' * 32000) is None
    assert len(vad.preroll) == 12 and not vad.frames and not vad.pending
    sound = array('h', [3000, -3000] * 2400).tobytes()  # 300ms
    assert vad.feed(sound[:101]) is None
    assert vad.feed(sound[101:]) is None
    pcm, long = vad.feed(b'\0' * 22400)
    assert not long and sound in pcm and len(pcm) <= fmt.bytes_per_second * 2
    vad = UtteranceBuffer(fmt, max_seconds=1)
    pcm, long = vad.feed(array('h', [3000] * 16000).tobytes())
    assert long and len(pcm) == fmt.bytes_per_second


def test_vad_short_click_is_not_speech():
    vad = UtteranceBuffer(PcmFormat(16000, 1))
    assert vad.feed(array('h', [3000] * 320).tobytes() + b'\0' * 24000) is None


def test_resampling_and_extended_whisper_limit():
    source, target = PcmFormat(16000, 1), PcmFormat(48000, 2)
    pcm = array('h', [1000] * 1600).tobytes()
    result = array('h', resample_pcm(pcm, source, target))
    assert len(result) == 9600 and set(result) == {1000}
    long = b'\0' * source.bytes_per_second * 10
    assert wav_bytes(long, source, max_seconds=30)
    with pytest.raises(ValueError): wav_bytes(long, source)


async def until(check):
    async with asyncio.timeout(2):
        while not check():
            await asyncio.sleep(.001)


def utterance(audio):
    audio.data(array('h', [3000, -3000] * 2400).tobytes())
    audio.data(b'\0' * 40000)


@pytest.fixture
def app():
    return QCoreApplication.instance() or QCoreApplication([])


def setup_conversation():
    audio = FakeAudioProbe()
    stt = Mock(available=lambda: True, transcribe=AsyncMock())
    tts = Mock(available=lambda: True, synthesize=AsyncMock(return_value=(b'\0'*3200, audio.format)), aclose=AsyncMock())
    answer = AsyncMock(return_value=Reply('Temperatura', 'W łazience jest 21 stopni.'))
    conv = ConversationController(lambda cb: audio, stt, tts, answer, cooldown=0)
    conv.set_connected(True)
    conv.start('', '')
    return conv, audio, stt, tts, answer


async def test_wake_question_spoken_reply_and_same_phrase_sleep(app):
    conv, audio, stt, tts, answer = setup_conversation()
    stt.transcribe.side_effect = [Transcription(t, .1) for t in
        ['Telewizor w tle', 'Klopsy', 'Jak ciepło jest w łazience?', 'Klopsy']]
    try:
        await until(lambda: audio.records == 1)
        utterance(audio)
        await until(lambda: audio.records == 2)
        answer.assert_not_called()
        tts.synthesize.assert_not_called()
        assert not conv.question
        utterance(audio)
        await until(lambda: audio.plays == 1)
        assert conv.active and conv.state == 'speaking' and audio.records == 2
        audio.done()
        await until(lambda: audio.records == 3)
        utterance(audio)
        await until(lambda: audio.plays == 2)
        answer.assert_awaited_once_with('Jak ciepło jest w łazience?')
        assert conv.answer == 'W łazience jest 21 stopni.'
        audio.done()
        await until(lambda: audio.records == 4)
        utterance(audio)
        await until(lambda: audio.plays == 3)
        assert not conv.active
        audio.done()
        await until(lambda: audio.records == 5)
        assert conv.enabled and conv.state == 'waiting'
    finally:
        await conv.aclose()
    assert audio.closed and not conv.enabled


async def test_stop_cancels_transcription_and_never_speaks_late(app):
    conv, audio, stt, tts, answer = setup_conversation()
    started = asyncio.Event()
    async def slow(*args):
        started.set()
        await asyncio.Event().wait()
    stt.transcribe.side_effect = slow
    await until(lambda: audio.records == 1)
    utterance(audio)
    await started.wait()
    conv.stop()
    await conv.aclose()
    tts.synthesize.assert_not_called()
    assert audio.closed


async def test_stop_during_playback_and_disconnect(app):
    conv, audio, stt, tts, answer = setup_conversation()
    stt.transcribe.return_value = Transcription('klopsy', .1)
    await until(lambda: audio.records == 1)
    utterance(audio)
    await until(lambda: audio.plays == 1)
    conv.set_connected(False)
    await conv.aclose()
    assert audio.closed and not conv.enabled and not conv.active
    answer.assert_not_called()


async def test_close_before_coroutine_start_releases_audio(app):
    conv, audio, *unused = setup_conversation()
    conv.stop()
    await conv.aclose()
    assert audio.closed


async def test_speech_failure_stops_capture(app):
    conv, audio, stt, tts, answer = setup_conversation()
    stt.transcribe.return_value = Transcription('Klopsy', .1)
    tts.synthesize.side_effect = RuntimeError('worker failed')
    await until(lambda: audio.records == 1)
    utterance(audio)
    await until(lambda: not conv.enabled)
    assert conv.state == 'error' and audio.closed
    await conv.aclose()


async def test_diagnostic_panel_close_preserves_conversation_shutdown_reaps_it(app):
    audio = FakeAudioProbe()
    stt = Mock(available=lambda: True, transcribe=AsyncMock())
    tts = Mock(available=lambda: True, aclose=AsyncMock())
    probe = AudioProbeController(lambda cb: audio, conversation_transcriber=stt,
                                 speaker=tts, answerer=lambda _: Reply('', ''))
    probe.set_connected(True)
    probe.openPanel()
    probe.startConversation('', '')
    await until(lambda: audio.records == 1)
    assert probe.busy
    probe.closePanel()
    assert probe.conversation.enabled
    await probe.aclose()
    assert audio.closed and not probe.conversation.enabled


async def test_auto_start_and_manual_off_survive_reconnect(app):
    settings = {}
    prefs = Mock()
    prefs.value.side_effect = lambda key, default, type: settings.get(key, default)
    prefs.setValue.side_effect = lambda key, value: settings.__setitem__(key, value)
    audio = FakeAudioProbe()
    conv = ConversationController(lambda cb: audio, Mock(available=lambda: True),
        Mock(available=lambda: True, aclose=AsyncMock()), Mock(), preferences=prefs)
    conv.set_connected(True)
    await until(lambda: audio.records == 1)
    assert settings['enabled'] is True and settings['input'] == 'mic'
    conv.stop()
    await asyncio.gather(conv._task, return_exceptions=True)
    assert settings['enabled'] is False
    conv.set_connected(False)
    conv.set_connected(True)
    assert not conv.enabled and audio.records == 1
    await conv.aclose()


async def test_repeated_stop_does_not_interrupt_worker_cleanup(app):
    conv, audio, stt, tts, answer = setup_conversation()
    started, release, finished = asyncio.Event(), asyncio.Event(), asyncio.Event()
    async def close():
        started.set()
        await release.wait()
        finished.set()
    tts.aclose.side_effect = close
    await until(lambda: audio.records == 1)
    conv.stop()
    await started.wait()
    conv.stop()
    release.set()
    await asyncio.gather(conv._task, return_exceptions=True)
    assert finished.is_set()
    await conv.aclose()


def test_question_allows_thinking_pause_and_thirty_second_audio():
    fmt = PcmFormat(16000, 1)
    vad = UtteranceBuffer(fmt, max_seconds=30, silence_seconds=1.2)
    sound = array('h', [3000, -3000] * 2400).tobytes()
    assert vad.feed(sound) is None
    assert vad.feed(b'\0' * 28800) is None  # 900ms inside a sentence
    assert vad.feed(sound) is None
    pcm, too_long = vad.feed(b'\0' * 40000)
    assert not too_long
    assert wav_bytes(b'\0' * fmt.bytes_per_second * 29, fmt, max_seconds=30)
    with pytest.raises(ValueError):
        wav_bytes(b'\0' * fmt.bytes_per_second * 31, fmt, max_seconds=30)
