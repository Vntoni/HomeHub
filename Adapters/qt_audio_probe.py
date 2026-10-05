"""Qt audio is loaded only when the user opens diagnostics; never at startup."""
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtMultimedia import QAudio, QAudioFormat, QAudioSink, QAudioSource, QMediaDevices

from Ports.audio_probe import PcmFormat


def is_respeaker(device):
    return "respeaker" in "".join(device.description().lower().split())


def device_key(device):
    return bytes(device.id()).hex()


def qt_format(fmt):
    result = QAudioFormat()
    result.setSampleRate(fmt.rate)
    result.setChannelCount(fmt.channels)
    result.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    return result


class QtAudioProbe:
    def __init__(self, on_devices_changed):
        self._devices = QMediaDevices()
        self._devices.audioInputsChanged.connect(on_devices_changed)
        self._devices.audioOutputsChanged.connect(on_devices_changed)
        self._source = self._sink = self._io = self._buffer = None

    def devices(self):
        def describe(devices):
            return [{"id": device_key(d), "label": d.description()} for d in devices]
        return (describe([d for d in self._devices.audioInputs() if is_respeaker(d)]),
                describe(self._devices.audioOutputs()))

    def _find(self, device_id, recording):
        devices = self._devices.audioInputs() if recording else self._devices.audioOutputs()
        for device in devices:
            if device_key(device) == device_id and (not recording or is_respeaker(device)):
                return device
        raise ValueError("Audio device disappeared")

    def record(self, device_id, on_data, on_error):
        self.stop()
        device = self._find(device_id, True)
        preferred = device.preferredFormat()
        # Native channel count is preserved. No assumed card index or default mic.
        candidates = [PcmFormat(preferred.sampleRate(), preferred.channelCount()),
                      PcmFormat(48000, 2), PcmFormat(16000, 1)]
        fmt = next((f for f in candidates if 8000 <= f.rate <= 96000 and 1 <= f.channels <= 4
                    and device.isFormatSupported(qt_format(f))), None)
        if fmt is None:
            raise ValueError("No supported bounded Int16 format")
        source = self._source = QAudioSource(device, qt_format(fmt))
        source.setBufferSize(fmt.bytes_per_second // 10)
        def state_changed(state):
            if self._source is source and source.error() != QAudio.Error.NoError:
                on_error()
        source.stateChanged.connect(state_changed)
        io = source.start()
        if self._source is not source or io is None or source.error() != QAudio.Error.NoError:
            self.stop()
            raise RuntimeError("Cannot open audio input")
        self._io = io
        def read():
            # Older PulseAudio QIODevices don't override bytesAvailable().
            # The audio source owns the hardware buffer and its byte count.
            while self._source is source and source.bytesAvailable() > 0:
                chunk = bytes(io.read(min(8192, source.bytesAvailable())))
                if not chunk:
                    break
                on_data(chunk)
        io.readyRead.connect(read)
        return fmt

    def play(self, device_id, pcm, fmt, on_done, on_error):
        self.stop()
        device = self._find(device_id, False)
        audio_format = qt_format(fmt)
        if not device.isFormatSupported(audio_format):
            raise ValueError("Output does not support recording format")
        buffer = self._buffer = QBuffer()
        buffer.setData(QByteArray(pcm))
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        sink = self._sink = QAudioSink(device, audio_format)
        sink.setVolume(.4)
        def state_changed(state):
            if self._sink is not sink:
                return
            if sink.error() != QAudio.Error.NoError:
                on_error()
            elif state == QAudio.State.IdleState:
                on_done()
        sink.stateChanged.connect(state_changed)
        sink.start(buffer)
        if self._sink is sink and sink.error() != QAudio.Error.NoError:
            self.stop()
            raise RuntimeError("Cannot open audio output")

    def stop(self):
        source, sink, buffer = self._source, self._sink, self._buffer
        self._source = self._sink = self._io = self._buffer = None
        if source is not None:
            source.stop()
            source.deleteLater()
        if sink is not None:
            sink.reset()  # Discard immediately; stop() can drain/block on Linux.
            sink.deleteLater()
        if buffer is not None:
            buffer.close()
            buffer.deleteLater()

    def close(self):
        self.stop()
        self._devices.audioInputsChanged.disconnect()
        self._devices.audioOutputsChanged.disconnect()
        self._devices.deleteLater()


def create_audio_probe(on_devices_changed):
    return QtAudioProbe(on_devices_changed)
