---
name: Alembic Files Must Be in Docker Image
description: Alembic migrations fail in production containers if alembic.ini and alembic/ directory are not explicitly copied into the image
type: feedback
---

# Alembic Files Must Be in Docker Image

**Extracted:** 2026-03-17
**Context:** FastAPI + Alembic backend in Docker, migrations run via `docker compose exec`

## Problem
Running `alembic upgrade head` inside a container fails with:

```
FAILED: No 'script_location' key found in configuration.
```

Root cause: `alembic.ini` (and the `alembic/` directory) live in the project root but are not included in `COPY` instructions in the Dockerfile — only `backend/` and `pnl_core/` (or equivalent source directories) are copied.

## Solution
Explicitly copy both `alembic.ini` and `alembic/` into the image:

```dockerfile
COPY pnl_core/ ./pnl_core/
COPY backend/  ./backend/
COPY alembic/  ./alembic/
COPY alembic.ini .
```

These are needed at container runtime when migrations run, not just at build time.

## When to Use
Any Python backend Dockerfile using Alembic where:
- Migrations are run via `docker compose exec backend alembic upgrade head`
- The Dockerfile does not have a blanket `COPY . .`
- Source directories are copied selectively (common pattern to avoid copying secrets, node_modules, etc.)