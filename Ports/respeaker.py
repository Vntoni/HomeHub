"""USB presence only: this port never opens an audio stream."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RespeakerStatus:
    connected: bool = False
    message: str = "ReSpeaker niepodłączony"


class RespeakerPresencePort(Protocol):
    def read_status(self) -> RespeakerStatus: ...
