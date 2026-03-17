"""
Adapter repozytorium – PostgreSQL przez asyncpg.
Implementuje ReadingRepositoryPort.
"""
import asyncpg
from datetime import datetime, timezone


class PostgresRepositoryAdapter:
    """
    Zapisuje i odczytuje dane z bazy PostgreSQL.
    Użycie:
        repo = PostgresRepositoryAdapter(dsn="postgresql://user:pass@localhost/baza_domowa")
        await repo.connect()
        await repo.save_sensor_reading("Salon", 21.5, 55.0, datetime.now(tz=timezone.utc))
    """

    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Stwórz connection pool i upewnij się że tabele istnieją."""
        self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
        await self._create_tables()
        print("[PostgresRepo] Połączono z bazą danych i sprawdzono schemat.")

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    # ------------------------------------------------------------------
    # Migracja / schemat (idempotentna – CREATE TABLE IF NOT EXISTS)
    # ------------------------------------------------------------------

    async def _create_tables(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id          BIGSERIAL PRIMARY KEY,
                    room        TEXT        NOT NULL,
                    temperature REAL        NOT NULL,
                    humidity    REAL        NOT NULL,
                    ts          TIMESTAMPTZ NOT NULL DEFAULT now()
                );

                CREATE INDEX IF NOT EXISTS idx_sensor_room_ts
                    ON sensor_readings (room, ts DESC);

                CREATE TABLE IF NOT EXISTS weather_readings (
                    id           BIGSERIAL PRIMARY KEY,
                    temp_out     REAL        NOT NULL,
                    humidity_out REAL        NOT NULL,
                    condition    TEXT        NOT NULL DEFAULT '',
                    wind_speed   REAL        NOT NULL DEFAULT 0,
                    ts           TIMESTAMPTZ NOT NULL DEFAULT now()
                );

                CREATE INDEX IF NOT EXISTS idx_weather_ts
                    ON weather_readings (ts DESC);

                CREATE TABLE IF NOT EXISTS power_readings (
                    id      BIGSERIAL PRIMARY KEY,
                    device  TEXT        NOT NULL,
                    watt_h  REAL        NOT NULL,
                    ts      TIMESTAMPTZ NOT NULL DEFAULT now()
                );

                CREATE INDEX IF NOT EXISTS idx_power_device_ts
                    ON power_readings (device, ts DESC);
            """)

    # ------------------------------------------------------------------
    # Zapis
    # ------------------------------------------------------------------

    async def save_sensor_reading(
        self, room: str, temperature: float, humidity: float, ts: datetime
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sensor_readings (room, temperature, humidity, ts)
                VALUES ($1, $2, $3, $4)
                """,
                room, temperature, humidity, ts,
            )

    async def save_weather_reading(
        self,
        temp_out: float,
        humidity_out: float,
        condition: str,
        wind_speed: float,
        ts: datetime,
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO weather_readings (temp_out, humidity_out, condition, wind_speed, ts)
                VALUES ($1, $2, $3, $4, $5)
                """,
                temp_out, humidity_out, condition, wind_speed, ts,
            )

    async def save_power_reading(
        self, device: str, watt_h: float, ts: datetime
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO power_readings (device, watt_h, ts)
                VALUES ($1, $2, $3)
                """,
                device, watt_h, ts,
            )

    # ------------------------------------------------------------------
    # Odczyt
    # ------------------------------------------------------------------

    async def get_sensor_history(
        self, room: str, since: datetime, until: datetime | None = None
    ) -> list[dict]:
        until = until or datetime.now(tz=timezone.utc)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT room, temperature, humidity, ts
                FROM sensor_readings
                WHERE room = $1 AND ts >= $2 AND ts <= $3
                ORDER BY ts ASC
                """,
                room, since, until,
            )
        return [dict(r) for r in rows]

    async def get_weather_history(
        self, since: datetime, until: datetime | None = None
    ) -> list[dict]:
        until = until or datetime.now(tz=timezone.utc)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT temp_out, humidity_out, condition, wind_speed, ts
                FROM weather_readings
                WHERE ts >= $1 AND ts <= $2
                ORDER BY ts ASC
                """,
                since, until,
            )
        return [dict(r) for r in rows]

    async def get_latest_sensor_reading(self, room: str) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT room, temperature, humidity, ts
                FROM sensor_readings
                WHERE room = $1
                ORDER BY ts DESC
                LIMIT 1
                """,
                room,
            )
        return dict(row) if row else None

    async def get_latest_weather_reading(self) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT temp_out, humidity_out, condition, wind_speed, ts
                FROM weather_readings
                ORDER BY ts DESC
                LIMIT 1
                """
            )
        return dict(row) if row else None


