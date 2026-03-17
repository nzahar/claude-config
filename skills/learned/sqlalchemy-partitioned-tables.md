# SQLAlchemy Async + PostgreSQL Partitioned Tables

**Extracted:** 2026-03-16
**Context:** When using SQLAlchemy ORM with PostgreSQL range-partitioned tables

## Problem

`Base.metadata.create_all()` cannot generate `PARTITION BY RANGE` DDL.
If the partitioned table model inherits from `Base`, calling `create_all()` creates
a regular (non-partitioned) table, breaking the schema or conflicting with raw DDL.

## Solution

1. **Define the table as a standalone `Table()` on a separate `MetaData()`** — keeps it out of `Base.metadata` so `create_all()` ignores it, while still allowing `pg_insert(table).on_conflict_do_update(...)`.

2. **Create the partitioned table + partitions via raw SQL in an `init_db()` function** — use `CREATE TABLE IF NOT EXISTS ... PARTITION BY RANGE` and idempotent `DO $$ ... END $$` blocks for partitions.

3. **Non-partitioned tables (jobs, uploads) can still use standard ORM models** with `Base`.

## Example

```python
# models.py
from sqlalchemy import Table, Column, Integer, Text, Date, MetaData

_pa_meta = MetaData()  # separate from Base.metadata

player_activity_table = Table(
    "player_activity",
    _pa_meta,
    Column("client_id", Integer, nullable=False),
    Column("player_id", Text, nullable=False),
    Column("report_date", Date, nullable=False),
    # ... other columns
)
```

```python
# database.py — init_db() with raw DDL
_INIT_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS player_activity (
        client_id INTEGER NOT NULL,
        player_id TEXT NOT NULL,
        report_date DATE NOT NULL,
        PRIMARY KEY (client_id, player_id, report_date)
    ) PARTITION BY RANGE (report_date)
    """,
    # Idempotent partition creation
    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_class WHERE relname = 'player_activity_2024'
        ) THEN
            CREATE TABLE player_activity_2024 PARTITION OF player_activity
                FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
        END IF;
    END $$
    """,
]
```

```python
# upsert.py — use the standalone Table for inserts
from sqlalchemy.dialects.postgresql import insert as pg_insert

stmt = pg_insert(player_activity_table).values(records)
stmt = stmt.on_conflict_do_update(
    index_elements=["client_id", "player_id", "report_date"],
    set_={col: getattr(stmt.excluded, col) for col in update_cols},
)
await session.execute(stmt)
```

## When to Use

- PostgreSQL table with `PARTITION BY RANGE/LIST/HASH`
- SQLAlchemy async (asyncpg) with ORM for other tables
- Need both ORM convenience for simple tables AND raw DDL for partitioned ones