---
name: ClickHouse parallel client workers — calibrate to ceil(N_cores / max_threads)
description: When fanning out independent CH queries via ThreadPoolExecutor, optimal worker count is ceil(N_cores / CH max_threads); higher values regress quadratically because per-query parallelism saturates CPU and queries stall each other
type: feedback
---

# ClickHouse parallel client workers — calibrate to ceil(N_cores / max_threads)

**Extracted:** 2026-05-14
**Context:** Building a Python-side fan-out (ThreadPoolExecutor / asyncio / multiprocessing) of independent CH queries against a single CH server, picking `--workers N` for throughput.

## Problem

Naive intuition: "more workers = faster, just match worker count to CPU cores." On a 24-core server with default CH `max_threads=8`, you might guess 8 or 16 workers.

What actually happens:

| `--workers` | per-query latency | aggregate throughput |
|---:|---:|---:|
| 1 | 8.5 s | 0.12 query/s |
| **3** | **8.5 s** | **0.31 query/s** ← linear scaling |
| 4 | **27 s** | 0.07 query/s ← worse than 1 worker |
| 8 | gridlock | ~0.04 query/s ← thrashes hard |

Past the sweet spot, throughput **regresses quadratically** because each CH query internally fans out to `max_threads` cores. Two queries × 8 threads = 16 cores active; four queries × 8 threads = 32 thread-cores requested on 24 physical cores → contention, context switching, cache thrashing. The total wall time per query inflates faster than parallelism gains compensate.

## Solution

```
optimal_workers = ceil(N_cores / CH_max_threads)
```

Look up `max_threads` from the CH server, divide your physical core count by it, ceiling. That's your worker count. Treat it as an upper bound — if other workloads share the box (vllm, other CH clients, background merges), drop one more.

To check `max_threads`:

```python
client.query(
    "SELECT name, value FROM system.settings WHERE name = 'max_threads'"
).result_rows
```

To check `system.processes` and recent query memory live:

```python
client.query(
    "SELECT count(), round(sum(memory_usage)/1024/1024/1024, 2) AS gb "
    "FROM system.processes WHERE query NOT LIKE '%system.processes%'"
).result_rows
```

## Example

24-core office server, `max_threads=8`, no other heavy CH workloads:

```
optimal = ceil(24 / 8) = 3 workers
```

Use that as the `ThreadPoolExecutor(max_workers=3)`. If you observe `top` showing CH at 1500 % CPU (~15 cores) under 3 workers, you're at the sweet spot — capacity used, no contention.

If you really want more parallelism, the only honest path is to drop CH `max_threads` per query (`SETTINGS max_threads=2`) so you can run more concurrent queries at less per-query parallelism. But query latency then goes up too — only worth it if individual queries have low intrinsic parallelism (small partitions, indexed lookups), where `max_threads=8` was wasted anyway.

## When to Use

Trigger on any of:
- Designing a ThreadPoolExecutor or asyncio gather around a `clickhouse-connect` / `clickhouse-driver` client where workers > 1
- Observing `clickhouse-server` at high CPU + queries serialised in `system.processes` despite low `max_concurrent_queries`
- Picking `--workers` flag for any CH-fanout script
- Performance regression when raising worker count

The formula is empirical and conservative — measure on your actual workload before committing for long-running ETL. A 5-template smoke run with `--workers 1, 2, 3, 4` is enough to see the regression curve.

Per-thread CH client is mandatory for this pattern: clickhouse-connect's HTTP client is **not** safe for concurrent queries on one connection. Use `threading.local()` to give each worker its own client (and bypass any `lru_cache` your project has around `get_client()`).
