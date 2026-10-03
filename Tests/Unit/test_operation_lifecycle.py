import asyncio
import threading

import pytest

from App.operations import OperationCoordinator, OperationBusy, run_blocking


async def test_timeout_retains_resource_until_real_thread_finishes_and_stops_next_step():
    entered, release = threading.Event(), threading.Event()
    steps, busy = [], []
    coordinator = OperationCoordinator(lambda key, value: busy.append(value))
    reconciled = asyncio.Event()
    def blocking():
        entered.set()
        assert release.wait(2)
        steps.append("worker")
    async def operation():
        await run_blocking(blocking)
        steps.append("forbidden-next-write")
    async def reconcile():
        assert not coordinator.busy("shared-client")
        reconciled.set()
    try:
        with pytest.raises(TimeoutError):
            await coordinator.run("shared-client", operation, timeout=.02, on_late_done=reconcile)
        assert entered.is_set() and coordinator.busy("shared-client")
        with pytest.raises(OperationBusy):
            await coordinator.run("shared-client", operation)
        with pytest.raises(OperationBusy):
            await coordinator.run("shared-client", operation, read=True)
        assert not reconciled.is_set()
        release.set()
        await asyncio.wait_for(reconciled.wait(), 1)
        assert steps == ["worker"]
        assert busy == [True, False]
    finally:
        release.set()
        await coordinator.close()


async def test_reads_coalesce_and_other_resources_are_independent():
    coordinator = OperationCoordinator()
    gate, entered = asyncio.Event(), asyncio.Event()
    calls = []
    async def reading():
        calls.append("read")
        entered.set()
        await gate.wait()
        return 42
    first = asyncio.create_task(coordinator.run("room", reading, read=True))
    await entered.wait()
    second = asyncio.create_task(coordinator.run("room", reading, read=True))
    assert await coordinator.run("other-room", lambda: asyncio.sleep(0, result=7)) == 7
    gate.set()
    assert await asyncio.gather(first, second) == [42, 42]
    assert calls == ["read"]
    await coordinator.close()


async def test_shutdown_rejects_new_operations_and_is_idempotent():
    coordinator = OperationCoordinator()
    gate = asyncio.Event()
    task = asyncio.create_task(coordinator.run("room", gate.wait))
    await asyncio.sleep(0)
    await coordinator.close()
    with pytest.raises(asyncio.CancelledError):
        await task
    with pytest.raises(RuntimeError):
        await coordinator.run("room", gate.wait)
    await coordinator.close()
