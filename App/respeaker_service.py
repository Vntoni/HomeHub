"""Optional, cancellable USB presence monitor; independent of device refresh."""
import asyncio
import logging
import math

from App.operations import run_blocking
from Ports.respeaker import RespeakerPresencePort, RespeakerStatus

logger = logging.getLogger(__name__)


class RespeakerService:
    def __init__(self, adapter: RespeakerPresencePort, poll_seconds=2.0):
        if not math.isfinite(poll_seconds) or poll_seconds <= 0:
            raise ValueError("USB polling interval must be positive and finite")
        self._adapter = adapter
        self._poll_seconds = poll_seconds

    async def run(self, on_change):
        previous = None
        while True:
            try:
                status = await run_blocking(self._adapter.read_status)
            except Exception as exc:
                status = RespeakerStatus(False, "Nie można sprawdzić połączenia ReSpeaker")
                if status != previous:
                    logger.warning("ReSpeaker USB probe failed (%s)", type(exc).__name__)
            if status != previous:
                on_change(status)
                previous = status
            await asyncio.sleep(self._poll_seconds)
