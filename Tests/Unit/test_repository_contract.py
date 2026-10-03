"""Query parameters and failure propagation, without a database connection."""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from Adapters.postgres_repository_adapter import PostgresRepositoryAdapter


@pytest.fixture
def repository():
    connection = AsyncMock()
    @asynccontextmanager
    async def acquire():
        yield connection
    repo = PostgresRepositoryAdapter("postgresql://test.invalid/homehub_test")
    repo._pool = Mock(acquire=acquire, close=AsyncMock())
    return repo, connection


async def test_sensor_values_are_bound_parameters_and_write_error_propagates(repository):
    repo, connection = repository
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    room = "test-room'; DROP TABLE sensor_readings; --"
    await repo.save_sensor_reading(room, 21.5, 48, timestamp)
    query, *parameters = connection.execute.call_args.args
    assert room not in query
    assert parameters == [room, 21.5, 48, timestamp]
    connection.execute.side_effect = ConnectionError("fake DB unavailable")
    with pytest.raises(ConnectionError):
        await repo.save_sensor_reading(room, 21.5, 48, timestamp)


async def test_missing_reading_and_close(repository):
    repo, connection = repository
    connection.fetchrow.return_value = None
    assert await repo.get_latest_sensor_reading("test-room") is None
    await repo.close()
    repo._pool.close.assert_awaited_once()
