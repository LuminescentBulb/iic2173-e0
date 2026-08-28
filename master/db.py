import json
import os
from collections.abc import AsyncGenerator
import asyncpg

DATABASE_URL = os.environ.get("DATABASE_URL")

pool: asyncpg.Pool | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    idpk TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    meta_content TEXT NOT NULL,
    constraints JSONB NOT NULL DEFAULT '{}'::jsonb,
    received_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS demands (
    id BIGSERIAL PRIMARY KEY,
    event_id BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    city TEXT NOT NULL,
    demand DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS demands_event_id_idx ON demands (event_id);
"""

async def init_conn(conn: asyncpg.Connection) -> None:
    for t in ("json", "jsonb"):
        await conn.set_type_codec(
            t, encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )


async def connect() -> None:
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, init=init_conn)
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA)


async def disconnect() -> None:
    if pool is not None:
        await pool.close()


async def get_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    async with pool.acquire() as conn:
        yield conn