import asyncio
from typing import Optional, Callable
from contextlib import suppress

from Ports.washer import WasherPort, WasherSnapshot


class WasherService:
    def __init__(self, washer: WasherPort, poll_seconds: float = 10.0):
        self._w = washer
        self._poll = poll_seconds
        self._task: Optional[asyncio.Task] = None
        self._on_snapshot: Optional[Callable[[WasherSnapshot], None]] = None

    async def _close_port(self) -> None:
        close = getattr(self._w, "aclose", None)
        if callable(close):
            await close()
            return

        close = getattr(self._w, "close", None)
        if callable(close):
            res = close()
            if asyncio.iscoroutine(res):
                await res

    async def start(self, on_snapshot: Callable[[WasherSnapshot], None]) -> None:
        if self._task and not self._task.done():
            return

        self._on_snapshot = on_snapshot

        async def _runner() -> None:
            try:
                while True:
                    try:
                        st = await self._w.snapshot(listen_seconds=8.0)
                        on_snapshot(st)
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        on_snapshot(WasherSnapshot(False, None, None))

                    try:
                        await asyncio.sleep(self._poll)
                    except asyncio.CancelledError:
                        raise
            finally:
                with suppress(Exception):
                    await self._close_port()

        self._task = asyncio.create_task(_runner(), name="WasherService._runner")

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self._task = None

        await self._close_port()
