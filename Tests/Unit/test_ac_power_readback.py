import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from App.climate_service import confirm_ac_power


async def test_delayed_confirmation_retries_reads_without_resending_commands():
    service = Mock(refresh=AsyncMock(), operating_mode=Mock(side_effect=["OFF", "OFF", "HEAT"]))
    await confirm_ac_power(service, "test-room", True, interval=0)
    assert service.refresh.await_count == 3
    service.turn_on.assert_not_called()


@pytest.mark.parametrize("mode", ["OFF", "UNKNOWN", None])
async def test_unconfirmed_on_never_returns_success(mode):
    service = Mock(refresh=AsyncMock(), operating_mode=Mock(return_value=mode))
    with pytest.raises(RuntimeError, match="not confirmed"):
        await confirm_ac_power(service, "test-room", True, interval=0)
    assert service.refresh.await_count == 4


async def test_refresh_failure_then_recovery():
    service = Mock(refresh=AsyncMock(side_effect=[ConnectionError(), None]),
                   operating_mode=Mock(return_value="HEAT"))
    await confirm_ac_power(service, "test-room", True, interval=0)
    assert service.refresh.await_count == 2


async def test_off_requires_explicit_off_readback():
    service = Mock(refresh=AsyncMock(), operating_mode=Mock(side_effect=["UNKNOWN", "OFF"]))
    await confirm_ac_power(service, "test-room", False, interval=0)
    assert service.refresh.await_count == 2


async def test_cancellation_propagates_without_further_reads():
    service = Mock(refresh=AsyncMock(side_effect=asyncio.CancelledError()))
    with pytest.raises(asyncio.CancelledError):
        await confirm_ac_power(service, "test-room", True, interval=0)
    service.refresh.assert_awaited_once()
