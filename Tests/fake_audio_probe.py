"""Explicit fake: no QtMultimedia import, audio access, files or network."""
from Ports.audio_probe import PcmFormat


class FakeAudioProbe:
    def __init__(self, on_devices_changed=None):
        self.on_devices_changed = on_devices_changed
        self.records = self.plays = self.stops = 0
        self.closed = False
        self.format = PcmFormat(16000, 1)
        self.input_devices = [{"id": "mic", "label": "ReSpeaker Lite (test)"}]
        self.output_devices = [{"id": "speaker", "label": "ReSpeaker Lite głośnik (test)"}]

    def devices(self): return self.input_devices, self.output_devices

    def record(self, device_id, on_data, on_error):
        assert device_id == "mic"
        self.records += 1
        self.data, self.error = on_data, on_error
        return self.format

    def play(self, device_id, pcm, fmt, on_done, on_error):
        assert device_id == "speaker"
        self.plays += 1
        self.played = pcm
        self.done, self.error = on_done, on_error

    def stop(self): self.stops += 1
    def close(self): self.closed = True
