from array import array
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QCoreApplication

from Compositions.demo import build_demo_backend
from Interface.qt_audio_probe import AudioProbeController
from Ports.audio_probe import PcmFormat
from Ports.respeaker import RespeakerStatus
from Tests.fake_audio_probe import FakeAudioProbe


@pytest.fixture
def probe():
    app = QCoreApplication.instance() or QCoreApplication([])
    fake = FakeAudioProbe()
    controller = AudioProbeController(lambda cb: fake)
    controller.set_connected(True)
    controller.openPanel()
    yield controller, fake
    controller.shutdown()


def sound():
    return array('h', [0, 16384, -32768, 0] * 100).tobytes()


def test_lazy_optional_and_no_automatic_recording():
    factory = Mock()
    p = AudioProbeController(factory)
    p.openPanel()
    factory.assert_not_called()
    p.closePanel()
    p.set_connected(True)
    factory.assert_not_called()
    assert not p.hasRecording and not p.busy
    demo = AudioProbeController()
    demo.set_connected(True)
    demo.openPanel()
    assert "demo" in demo.message


def test_record_explicitly_then_stop_play_and_delete(probe):
    p, fake = probe
    assert fake.records == fake.plays == 0
    p.record("mic")
    fake.data(sound())
    assert p.state == "recording" and p.level == 1.0
    p.record("mic")
    p.play("speaker")
    assert fake.records == 1 and fake.plays == 0
    p.stop()
    assert p.hasRecording and p.state == "idle" and p.level == 0
    p.play("speaker")
    assert p.state == "playing" and fake.played == sound()
    p.record("mic")
    assert fake.records == 1  # Half-duplex.
    fake.done()
    assert p.state == "idle" and p.hasRecording
    p.clear()
    assert not p.hasRecording and not p._pcm


def test_time_and_memory_bounds_frame_alignment_and_late_callbacks(probe):
    p, fake = probe
    p.record("mic")
    old_data = fake.data
    fake.data(b'\0' * (fake.format.bytes_per_second * 20))
    assert len(p._pcm) == fake.format.bytes_per_second * 5
    assert not p.busy and not p._timer.isActive()
    p.record("mic")
    old_data(sound())
    assert not p._pcm
    fake.data(b'\0\0\0')
    p._deadline()
    assert bytes(p._pcm) == b'\0\0'
    assert "cichy" in p.message


@pytest.mark.parametrize("ending", ["closePanel", "disconnect", "devices", "shutdown", "error"])
def test_interrupt_discards_capture_and_ignores_late_audio(probe, ending):
    p, fake = probe
    p.record("mic")
    fake.data(sound())
    old_data = fake.data
    if ending == "disconnect":
        p.set_connected(False)
    elif ending == "devices":
        p._devices_changed()
    elif ending == "error":
        fake.error()
    else:
        getattr(p, ending)()
    old_data(sound())
    assert not p.hasRecording and not p.busy and not p._timer.isActive()
    if ending == "shutdown":
        p.openPanel()
        p.record("mic")
        assert fake.records == 1 and fake.closed


def test_disconnect_during_playback_and_reconnect_requires_new_click(probe):
    p, fake = probe
    p.record("mic")
    fake.data(sound())
    p.stop()
    p.play("speaker")
    done = fake.done
    p.set_connected(False)
    p.set_connected(True)
    done()
    assert fake.records == 1 and fake.plays == 1
    assert not p.busy and not p.hasRecording
    p.record("mic")
    assert fake.records == 2


def test_no_default_device_fallback(probe):
    p, fake = probe
    p.record("default")
    assert fake.records == 0
    p.record("mic")
    fake.data(sound())
    p.stop()
    p.play("default")
    assert fake.plays == 0 and p.hasRecording


def test_missing_audio_library_is_optional():
    def unavailable(_): raise ImportError("private platform details")
    p = AudioProbeController(unavailable)
    p.set_connected(True)
    p.openPanel()
    assert p.state == "error" and "private" not in p.message
    p.shutdown()


def test_no_samples_and_playback_deadline(probe):
    p, fake = probe
    p.record("mic")
    p._deadline()
    assert not p.hasRecording and "Brak próbek" in p.message
    p.record("mic")
    fake.data(sound())
    p.stop()
    p.play("speaker")
    p._deadline()
    assert p.state == "error" and not p.hasRecording


@pytest.mark.parametrize("method", ["record", "play"])
def test_audio_open_error_is_contained(probe, method):
    p, fake = probe
    if method == "play":
        p.record("mic")
        fake.data(sound())
        p.stop()
    setattr(fake, method, Mock(side_effect=RuntimeError("private error")))
    getattr(p, method)("mic" if method == "record" else "speaker")
    assert p.state == "error" and not p.busy and not p.hasRecording
    assert "private" not in p.message


def test_invalid_format_stops_transport(probe):
    p, fake = probe
    fake.format = PcmFormat(192000, 20)
    p.record("mic")
    assert not p.busy and p.state == "error"


async def test_backend_stops_audio_before_waiting_for_device_cleanup():
    backend = await build_demo_backend()
    fake = FakeAudioProbe()
    backend.audioProbe._factory = lambda cb: fake
    backend._on_respeaker_status(RespeakerStatus(True, "USB"))
    backend.audioProbe.openPanel()
    backend.audioProbe.record("mic")
    fake.data(sound())
    async def cleanup():
        assert fake.closed and not backend.audioProbe.hasRecording
    backend._operations.close = cleanup
    await backend.shutdown()
