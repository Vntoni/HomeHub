"""A complete, immutable device reading, committed only after validation."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math


@dataclass(frozen=True)
class DeviceSnapshot:
    current: float
    target: float
    mode: str
    power: bool
    confirmed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if not all(math.isfinite(value) for value in (self.current, self.target)):
            raise ValueError("Incomplete temperature reading")
        if not self.mode or self.mode.lower() in {"unknown", "none"}:
            raise ValueError("Incomplete mode reading")
        if type(self.power) is not bool:
            raise ValueError("Incomplete power reading")
