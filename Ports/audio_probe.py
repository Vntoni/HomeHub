"""Small local diagnostic contract. PCM is signed 16-bit, native endian."""
from dataclasses import dataclass
from typing import Callable, Protocol


@dataclass(frozen=True)
class PcmFormat:
    rate: int
    channels: int

    @property
    def frame_bytes(self):
        return self.channels * 2

    @property
    def bytes_per_second(self):
        return self.rate * self.frame_bytes


class AudioProbePort(Protocol):
    def devices(self) -> tuple[list[dict], list[dict]]: ...
    def record(self, device_id: str, on_data: Callable, on_error: Callable) -> PcmFormat: ...
    def play(self, device_id: str, pcm: bytes, fmt: PcmFormat, on_done: Callable, on_error: Callable): ...
    def stop(self): ...
    def close(self): ...
