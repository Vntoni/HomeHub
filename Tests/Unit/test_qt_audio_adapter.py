"""Replace every native audio entry point; only QBuffer/QAudioFormat are real."""
from unittest.mock import Mock
import pytest
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from Adapters import qt_audio_probe as audio
from Ports.audio_probe import PcmFormat


class Signal:
    def __init__(self): self.callbacks = []
    def connect(self, cb): self.callbacks.append(cb)
    def disconnect(self): self.callbacks.clear()
    def emit(self, *args):
        for cb in list(self.callbacks): cb(*args)


class Device:
    def __init__(self, name, key): self.name, self.key = name, key
    def description(self): return self.name
    def id(self): return QByteArray(self.key)
    def preferredFormat(self): return audio.qt_format(PcmFormat(48000, 2))
    def isFormatSupported(self, fmt): return fmt.sampleRate() == 48000 and fmt.channelCount() == 2


@pytest.fixture
def adapter(monkeypatch):
    mic, other, speaker = Device("ReSpeaker Lite", b'usb-mic'), Device("Laptop microphone", b'other'), Device("ReSpeaker speaker", b'usb-speaker')
    devices = Mock(audioInputs=Mock(return_value=[other, mic]), audioOutputs=Mock(return_value=[speaker]),
                   audioInputsChanged=Signal(), audioOutputsChanged=Signal())
    monkeypatch.setattr(audio, "QMediaDevices", lambda: devices)
    sources, sinks = [], []
    class Source:
        def __init__(self, device, fmt):
            self.device, self.fmt = device, fmt
            self.stateChanged = Signal()
            self.code = audio.QAudio.Error.NoError
            self.stopped = False
            sources.append(self)
        def error(self): return self.code
        def setBufferSize(self, size): pass
        def start(self):
            self.io = QBuffer()
            self.io.setData(b'\0' * 16000)
            self.io.open(QIODevice.OpenModeFlag.ReadOnly)
            return self.io
        def stop(self): self.stopped = True
        def deleteLater(self): pass
    class Sink:
        def __init__(self, device, fmt):
            self.device = device
            self.stateChanged = Signal()
            self.reset_called = False
            sinks.append(self)
        def error(self): return audio.QAudio.Error.NoError
        def setVolume(self, volume): self.volume = volume
        def start(self, buffer): self.buffer = buffer
        def reset(self): self.reset_called = True
        def deleteLater(self): pass
    monkeypatch.setattr(audio, "QAudioSource", Source)
    monkeypatch.setattr(audio, "QAudioSink", Sink)
    changed = Mock()
    probe = audio.QtAudioProbe(changed)
    yield probe, devices, sources, sinks, changed
    probe.close()


def test_filter_and_no_open_during_enumeration(adapter):
    probe, devices, sources, sinks, changed = adapter
    inputs, outputs = probe.devices()
    assert inputs == [{'id': b'usb-mic'.hex(), 'label': 'ReSpeaker Lite'}]
    assert outputs[0]['id'] == b'usb-speaker'.hex()
    assert sources == sinks == []
    devices.audioInputsChanged.emit()
    changed.assert_called_once()
    with pytest.raises(ValueError):
        probe.record(b'other'.hex(), Mock(), Mock())


def test_capture_format_data_error_and_shutdown(adapter):
    probe, devices, sources, sinks, changed = adapter
    received, failed = [], Mock()
    fmt = probe.record(b'usb-mic'.hex(), received.append, failed)
    assert fmt == PcmFormat(48000, 2)
    source = sources[0]
    source.io.readyRead.emit()
    assert sum(map(len, received)) == 16000
    assert max(map(len, received)) <= 8192
    source.code = audio.QAudio.Error.IOError
    source.stateChanged.emit(audio.QAudio.State.StoppedState)
    failed.assert_called_once()
    probe.stop()
    source.stateChanged.emit(audio.QAudio.State.StoppedState)
    assert failed.call_count == 1 and source.stopped


def test_playback_uses_explicit_output_memory_and_immediate_reset(adapter):
    probe, devices, sources, sinks, changed = adapter
    done, fail = Mock(), Mock()
    probe.play(b'usb-speaker'.hex(), b'\0' * 16, PcmFormat(48000, 2), done, fail)
    sink = sinks[0]
    assert bytes(sink.buffer.readAll()) == b'\0' * 16
    assert sink.volume == .4 and not sources
    sink.stateChanged.emit(audio.QAudio.State.IdleState)
    done.assert_called_once()
    probe.stop()
    assert sink.reset_called
    sink.stateChanged.emit(audio.QAudio.State.IdleState)
    assert done.call_count == 1


def test_removed_device_or_unsupported_output_does_not_fallback(adapter):
    probe, devices, sources, sinks, changed = adapter
    with pytest.raises(ValueError):
        probe.play(b'usb-speaker'.hex(), b'\0\0', PcmFormat(16000, 1), Mock(), Mock())
    devices.audioInputs.return_value = []
    with pytest.raises(ValueError):
        probe.record(b'usb-mic'.hex(), Mock(), Mock())
    assert sources == sinks == []
