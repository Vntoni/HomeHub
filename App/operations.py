"""Own device operations until their transport has actually stopped."""
import asyncio
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class OperationBusy(RuntimeError):
    pass


async def run_blocking(method, *args, **kwargs):
    """Cancellation stops the caller's sequence, but waits for its real worker.

    The coordinator shields this coroutine from its UI waiter, so a UI timeout
    can return while this task still owns the device until the thread ends.
    """
    worker = asyncio.create_task(asyncio.to_thread(method, *args, **kwargs))
    try:
        return await asyncio.shield(worker)
    except asyncio.CancelledError:
        while not worker.done():
            try:
                await asyncio.shield(worker)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if not worker.cancelled() and worker.exception() is not None:
            logger.warning("Cancelled device worker failed (%s)", type(worker.exception()).__name__)
        raise


@dataclass
class _Operation:
    task: asyncio.Task
    read: object
    abandoned: bool = False


class OperationCoordinator:
    def __init__(self, on_busy=None):
        self._active = {}
        self._background = set()
        self._closed = False
        self._on_busy = on_busy

    def busy(self, key):
        return key in self._active

    async def run(self, key, factory, *, timeout=45, read=False, on_late_done=None):
        if self._closed:
            raise RuntimeError("Device operations are closing")
        entry = self._active.get(key)
        owner = entry is None
        if entry is not None and not (read and entry.read == read):
            raise OperationBusy("Device transport is still busy")
        if owner:
            entry = _Operation(asyncio.create_task(factory()), read)
            self._active[key] = entry
            if self._on_busy:
                self._on_busy(key, True)
            entry.task.add_done_callback(lambda task: self._finished(key, entry, on_late_done))
        try:
            async with asyncio.timeout(timeout):
                return await asyncio.shield(entry.task)
        except (TimeoutError, asyncio.CancelledError):
            if owner:
                entry.abandoned = True
                if not entry.task.cancelling():
                    entry.task.cancel()
            raise

    def _finished(self, key, entry, on_late_done):
        if self._active.get(key) is entry:
            del self._active[key]
        if not entry.task.cancelled():
            entry.task.exception()  # Retrieve errors even when the UI has left.
        if self._on_busy:
            self._on_busy(key, False)
        if entry.abandoned and on_late_done and not self._closed:
            task = asyncio.create_task(on_late_done())
            self._background.add(task)
            task.add_done_callback(self._background_finished)

    def _background_finished(self, task):
        self._background.discard(task)
        if not task.cancelled() and task.exception() is not None:
            logger.warning("Late device readback failed (%s)", type(task.exception()).__name__)

    async def close(self, timeout=5):
        self._closed = True
        tasks = {entry.task for entry in self._active.values()} | self._background
        for task in tasks:
            if not task.cancelling():
                task.cancel()
        if tasks:
            _, pending = await asyncio.wait(tasks, timeout=timeout)
            if pending:
                raise TimeoutError("Device transports are still running during shutdown")
