from datetime import date, datetime, timedelta
from typing import Any
import asyncpg
from pydantic import BaseModel
from fastapi import Depends, FastAPI, HTTPException, Query
from contextlib import asynccontextmanager
import db

class Demand(BaseModel):
    city: str
    demand: float
    unit: str


class PackageBody(BaseModel):
    demands: list[Demand]
    validUntil: datetime
    metaContent: str
    constraints: dict[str, Any]


class Event(BaseModel):
    idpk: str
    type: str
    packageBody: PackageBody
    receivedAt: datetime


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.disconnect()


app = FastAPI(lifespan=lifespan)


@app.post("/events")
async def receive_event(event: Event, conn: asyncpg.Connection = Depends(db.get_conn)):
    async with conn.transaction():
        event_id = await conn.fetchval(
            """
            INSERT INTO events (idpk, type, valid_until, meta_content, constraints, received_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (idpk) DO NOTHING
            RETURNING id
            """,
            event.idpk,
            event.type,
            event.packageBody.validUntil,
            event.packageBody.metaContent,
            event.packageBody.constraints,
            event.receivedAt,
        )

        if event_id is None:
            return {"message": "Event already exists"}

        # now can make demand insertions
        for demand in event.packageBody.demands:
            await conn.execute(
                """
                INSERT INTO demands (event_id, city, demand, unit)
                VALUES ($1, $2, $3, $4)
                """,
                event_id,
                demand.city,
                demand.demand,
                demand.unit,
            )
    return {"message": "Event received successfully"}


@app.get("/history")
async def get_history(
    page: int = Query(default = 1, ge=1),
    limit: int = Query(default = 25, ge=1),

    idpk: str | None = None,
    type: str | None = None,
    receivedAt: date | None = None,
    validUntil: date | None = None,
    metaContent: str | None = None,

    city: str | None = None,
    unit: str | None = None,
    demand: float | None = None,

    conn: asyncpg.Connection = Depends(db.get_conn)
):
    conditions = []
    params = []

    def add_param(value) -> str:
        params.append(value)
        return f"${len(params)}"

    # Event filters
    if idpk is not None:
        p = add_param(idpk)
        conditions.append(f"e.idpk = {p}")

    if type is not None:
        p = add_param(type)
        conditions.append(f"e.type = {p}")

    if metaContent is not None:
        p = add_param(metaContent)
        conditions.append(f"e.meta_content = {p}")

    # Dates
    if receivedAt is not None:
        start = datetime.combine(receivedAt, datetime.min.time())
        end = start + timedelta(days=1)

        p_start = add_param(start)
        p_end = add_param(end)

        conditions.append(
            f"e.received_at >= {p_start} AND e.received_at < {p_end}"
        )
    
    if validUntil is not None:
        start = datetime.combine(validUntil, datetime.min.time())
        end = start + timedelta(days=1)

        p_start = add_param(start)
        p_end = add_param(end)

        conditions.append(
            f"e.valid_until >= {p_start} AND e.valid_until < {p_end}"
        )

    # Demand filters
    demand_conditions = []

    if city is not None:
        p = add_param(city)
        demand_conditions.append(f"d.city = {p}")

    if unit is not None:
        p = add_param(unit)
        demand_conditions.append(f"d.unit = {p}")

    if demand is not None:
        p = add_param(demand)
        demand_conditions.append(f"d.demand = {p}")

    if demand_conditions:
        conditions.append(
            f"EXISTS (SELECT 1 FROM demands d WHERE d.event_id = e.id AND {' AND '.join(demand_conditions)})"
        )

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    offset = (page - 1) * limit
    p_limit = add_param(limit)
    p_offset = add_param(offset)

    rows = await conn.fetch(
        f"""
        SELECT
            e.id,
            e.idpk,
            e.type,
            e.valid_until,
            e.meta_content,
            e.constraints,
            e.received_at,

            COALESCE(
                (
                    SELECT jsonb_agg (
                        jsonb_build_object(
                            'city', d.city,
                            'demand', d.demand,
                            'unit', d.unit
                        )
                        ORDER BY d.id
                    )
                    FROM demands d
                    WHERE d.event_id = e.id
                ),
                '[]'::jsonb
            ) AS demands
        FROM events e

        {where_clause}

        ORDER BY e.received_at DESC
        LIMIT {p_limit} OFFSET {p_offset}
        """,
        *params
    )

    return [dict(row) for row in rows]


@app.get("/history/{id}")
async def get_history_by_id(
    id: int,
    conn: asyncpg.Connection = Depends(db.get_conn),
):
    row = await conn.fetchrow(
        """
        SELECT
            e.id,
            e.idpk,
            e.type,
            e.valid_until,
            e.meta_content,
            e.constraints,
            e.received_at,

            COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'city', d.city,
                            'demand', d.demand,
                            'unit', d.unit
                        )
                        ORDER BY d.id
                    )
                    FROM demands d
                    WHERE d.event_id = e.id
                ),
                '[]'::jsonb
            ) AS demands
        FROM events e
        WHERE e.id = $1
        """,
        id,
    )

    if row is None:
        raise HTTPException(status_code=404, detail="event not found")

    return dict(row)


# needed for RNF7
@app.get("/health")
async def health():
    return {"status": "ok"}
