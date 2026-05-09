---
name: FastAPI Async Background Tasks Don't Block the Event Loop
description: Async FastAPI BackgroundTasks calling sync CPU-heavy code (pandas, openpyxl, file I/O) blocks the entire server — wrap with asyncio.to_thread()
type: feedback
---

# FastAPI Async Background Tasks — Don't Block the Event Loop

**Extracted:** 2026-03-16
**Context:** FastAPI background tasks that call sync CPU-heavy code (pandas, Excel, ML)

## Problem

FastAPI's `BackgroundTasks` runs `async` functions directly on the event loop.
If an async background task calls sync CPU-heavy code (e.g., `pd.read_excel()`,
`build_report()`, file I/O), the **entire server blocks** — no requests are
served until the sync call finishes.

Sync (non-async) background tasks are automatically run in a thread pool,
but async ones are not.

## Solution

Wrap every sync/CPU-heavy call inside async background tasks with `asyncio.to_thread()`:

```python
async def _process_upload(upload_id: UUID, file_path: str) -> None:
    # DB operations — async, fine on event loop
    await _update_status(upload_id, "processing")

    # CPU-heavy sync work — MUST offload to thread
    raw_df = await asyncio.to_thread(load_excel, file_path)
    df = await asyncio.to_thread(preprocess_base_df, raw_df)

    # Back to async DB work
    async with AsyncSessionLocal() as session:
        await upsert_player_activity(session, df)
```

## When NOT needed

- Pure async I/O (DB queries via asyncpg, HTTP via httpx) — already non-blocking
- Trivial sync operations (dict construction, string formatting) — negligible

## When to Use

- Any FastAPI `async` background task calling: pandas, openpyxl, xlsxwriter,
  numpy-heavy computation, file parsing, image processing, or any function
  that takes >50ms of CPU time
- Rule of thumb: if it touches pandas or parses files, wrap it