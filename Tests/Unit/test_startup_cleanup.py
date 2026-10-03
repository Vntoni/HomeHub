import asyncio
from unittest.mock import Mock

import pytest

from App.lifecycle import build_with_resources


@pytest.mark.parametrize("failure_after", range(1, 5))
@pytest.mark.parametrize("cancelled", [False, True])
async def test_partial_build_releases_every_acquired_resource_in_reverse_order(failure_after, cancelled):
    closed = []
    async def close(index):
        closed.append(index)
    async def factory(resources):
        for index in range(4):
            resources.push_async_callback(close, index)
            if index + 1 == failure_after:
                if cancelled:
                    raise asyncio.CancelledError()
                raise RuntimeError("startup failed")
    with pytest.raises(asyncio.CancelledError if cancelled else RuntimeError):
        await build_with_resources(factory)
    assert closed == list(reversed(range(failure_after)))


async def test_successful_build_transfers_ownership_without_closing_early():
    closed = []
    backend = Mock()
    async def close():
        closed.append(True)
    async def factory(resources):
        resources.push_async_callback(close)
        return backend
    assert await build_with_resources(factory) is backend
    assert not closed
    scope = backend.register_resource.call_args.args[0]
    await scope.aclose()
    await scope.aclose()
    assert closed == [True]
