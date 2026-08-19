---
name: clickhouse
description: "ClickHouse gotchas learned the hard way — use whenever writing or tuning ClickHouse queries or clickhouse-connect client code: long IN-lists / queries over 256 KiB (max_query_size must go via HTTP settings, not a SQL SETTINGS clause), fan-out of parallel queries (worker count = ceil(N_cores / max_threads), per-thread clients), and a server-side label-propagation diagnostic to check whether transitive closure is safe before entity resolution."
---

# ClickHouse gotchas

# ClickHouse max_query_size — pass via HTTP settings, not SQL SETTINGS clause

**Context:** Building a CH query whose body (typically a long IN-list) exceeds the default 256 KiB parser limit, when the natural instinct is to append `SETTINGS max_query_size = N` to the SQL.

## Problem

You build a query like:

```sql
SELECT xpath, groupUniqArray(500)(value)
FROM raw_table
WHERE xpath IN ('xpath1', 'xpath2', ..., 'xpath7000')   -- ~1.1 MB of strings
GROUP BY xpath
SETTINGS max_query_size = 16777216
```

CH returns:

```
Code: 62. DB::Exception: Max query size exceeded
(can be increased with the `max_query_size` setting):
Syntax error: failed at position 261816 ('Данные_о_проведённых_исследованиях_...')
(SYNTAX_ERROR)
```

The error message helpfully suggests "increase max_query_size" — but raising the in-SQL setting **does not work**. Position 261,816 ≈ the default 256 KiB cutoff. The query bombs at parse time, **before** the parser ever sees the `SETTINGS` token at the tail.

## Solution

Pass `max_query_size` as an **HTTP-level setting** through the clickhouse-connect client's `settings=` parameter (or via URL `?max_query_size=N` if you're hitting the raw HTTP API). The HTTP layer applies it before the parser starts.

```python
# clickhouse-connect (Python)
client.query(
    sql,
    parameters={"xpaths": xpaths},
    settings={"max_query_size": "16777216"},  # 16 MiB
).result_rows
```

```bash
# raw HTTP
curl 'http://localhost:8123/?max_query_size=16777216' --data @big_query.sql
```

For `clickhouse-client` CLI: `--max_query_size=16777216` as a command-line flag works (also pre-parser).

Memory cost: parser memory at 16 MiB ≈ 50 MB per query — trivial on any modern server.

## Example

The full fix from a real production case (sample fetcher batching ~7000 xpaths in IN-list per query):

```python
def fetch_samples_for_table(client, table_name, xpaths):
    sql = (
        f"SELECT xpath, groupUniqArray(500)(value) AS samples "
        f"FROM `{table_name}` "
        f"WHERE xpath IN %(xpaths)s "
        f"GROUP BY xpath"
        # NO `SETTINGS max_query_size = ...` here — it would not apply.
    )
    return client.query(
        sql,
        parameters={"xpaths": xpaths},
        settings={"max_query_size": "16777216"},
    ).result_rows
```

## When to Use

Trigger on any of:
- CH error code **62** (`SYNTAX_ERROR`) with message "Max query size exceeded"
- A query whose IN-list, VALUES clause, or constant array is large (anything > ~200 KiB of SQL text)
- Any case where you wrote `SETTINGS max_query_size = N` at the end of the SQL and it appears to have no effect

Confusion is common because the error message and most CH documentation imply the SETTINGS clause is the right place. It works for **runtime** settings (memory, threads, timeouts) but NOT for parser-level limits, which need to be in effect before parsing begins.

Same pattern applies to `max_ast_elements` and any other parse-time setting.


---

# ClickHouse parallel client workers — calibrate to ceil(N_cores / max_threads)

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


---

# ClickHouse Connected Components Diagnostic via Label Propagation

**Context:** Identity resolution / entity deduplication problems where you need to decide if transitive closure (merging entities through shared evidence) is safe before committing to it.

## Problem

You have an entity resolution problem like:
- Same patient under multiple GUIDs across data sources, with overlap evidence per shared document.
- Same product under multiple SKUs, with overlap per shared barcode.
- Same user under multiple IDs, with overlap per shared device fingerprint.

The natural fix is **transitive closure**: build a graph (vertices = entity IDs, edges = pairs sharing evidence), find connected components, treat each component as one "real" entity.

But transitive closure has a hidden risk: **a single false-positive edge collapses the entire dataset into one giant component**. If your evidence column has any cross-entity collisions (e.g., a document_id reused across unrelated patients), components explode.

You need to know whether transitive closure is safe **before** committing to it as your dedup strategy.

## Solution

Run server-side label propagation in ClickHouse on the candidate graph, measure component-size distribution. If max component size and high-percentile sizes are small (single-digit), graph is healthy — transitive closure is safe. If there's a giant component, it indicates evidence collisions and dedup needs different design.

**Algorithm:**
1. Build edge list from your evidence source.
2. Initialize each vertex's label = itself.
3. Iterate: each vertex takes `min(label)` of its neighbors. Repeat until no labels change.
4. Group vertices by final label → connected components.
5. Report distribution.

**Convergence:** for graphs dominated by 2-way components (most real-world dedup graphs), converges in 2-4 iterations. Hard cap 20 as safety net.

## Example

```python
"""Connected components diagnostic for entity resolution."""
from your_db_module import get_client
import time


def run_diagnostic(client, edges_source_sql: str, vertices_source_sql: str):
    """
    edges_source_sql: produces (id_a, id_b) pairs of evidence-overlapping entities.
    vertices_source_sql: produces distinct entity ids that participate in edges.
    """
    # DDL
    for t in ("_eq_edges", "_eq_label", "_eq_label_next"):
        client.command(f"DROP TABLE IF EXISTS {t}")
    client.command("CREATE TABLE _eq_edges (id_a UUID, id_b UUID) ENGINE = MergeTree ORDER BY id_a")
    client.command("CREATE TABLE _eq_label (id UUID, label UUID) ENGINE = MergeTree ORDER BY id")
    client.command("CREATE TABLE _eq_label_next (id UUID, label UUID) ENGINE = MergeTree ORDER BY id")

    # Build edges (both directions for symmetric propagation)
    client.command(f"INSERT INTO _eq_edges {edges_source_sql}")

    # Initialise: each vertex's label = itself
    client.command(f"INSERT INTO _eq_label SELECT DISTINCT id, id AS label FROM ({vertices_source_sql})")

    # Iterate
    MAX_ITER = 20
    for i in range(1, MAX_ITER + 1):
        t0 = time.monotonic()
        client.command("TRUNCATE TABLE _eq_label_next")
        # One propagation step: label = min(own_label, min over neighbors of neighbor's label)
        client.command("""
            INSERT INTO _eq_label_next (id, label)
            SELECT
                l.id,
                least(l.label, ifNull(neighbors.min_label, l.label)) AS new_label
            FROM _eq_label AS l
            LEFT JOIN (
                SELECT e.id_a AS id, min(l2.label) AS min_label
                FROM _eq_edges AS e
                INNER JOIN _eq_label AS l2 ON l2.id = e.id_b
                GROUP BY e.id_a
            ) AS neighbors ON neighbors.id = l.id
        """)
        # Convergence check
        changed = int(client.query("""
            SELECT count() FROM _eq_label l
            INNER JOIN _eq_label_next n ON l.id = n.id
            WHERE l.label != n.label
        """).result_rows[0][0])
        # Swap
        client.command("TRUNCATE TABLE _eq_label")
        client.command("INSERT INTO _eq_label SELECT id, label FROM _eq_label_next")
        print(f"  iter {i}: {changed:,} changed in {time.monotonic() - t0:.1f}s")
        if changed == 0:
            print(f"  CONVERGED at iter {i}")
            break

    # Distribution
    rows = client.query("""
        SELECT component_size, count() AS n
        FROM (SELECT label, count() AS component_size FROM _eq_label GROUP BY label)
        GROUP BY component_size
        ORDER BY component_size
    """).result_rows
    for size, n in rows:
        print(f"  size={size:,}  components={n:,}  vertices={size*n:,}")

    rows = client.query("""
        SELECT
            max(component_size) AS max_sz,
            quantilesExact(0.5, 0.9, 0.99, 0.999)(component_size) AS qs
        FROM (SELECT count() AS component_size FROM _eq_label GROUP BY label)
    """).result_rows
    max_sz, (p50, p90, p99, p999) = rows[0]
    print(f"  max={max_sz}  p50={p50}  p90={p90}  p99={p99}  p999={p999}")

    # Cleanup
    for t in ("_eq_edges", "_eq_label", "_eq_label_next"):
        client.command(f"DROP TABLE IF EXISTS {t}")
```

**Decision rule based on diagnostic output:**

- `max_sz <= ~10` and `p99 <= ~5` → graph is healthy (mostly small components), transitive closure SAFE. Proceed with merge.
- `max_sz` in low hundreds, distribution has long tail → marginal. Inspect what those large components contain before deciding.
- `max_sz >>` rest of distribution (e.g., one component of 100k, all others ≤5) → GIANT COMPONENT. There's an evidence collision; transitive closure UNSAFE. Find and remove false-positive edges before retrying.

## Real numbers from production usage

In a patient dedup pipeline (385k GUIDs, 13.8M directed edges from document overlap):
- Converged in 3 iterations.
- 95.7% size-2 components (185k pairs).
- 4.27% size-3.
- 0.01% size-4.
- max=4. p99=3, p999=3.

→ Decision: transitive closure SAFE. No giant component. Confirmed pattern of real-world re-anonymization (one person under 2-3 GUIDs), not collision.

## When to Use

Trigger conditions:
- Designing identity resolution / dedup pipeline based on transitive closure of overlap evidence.
- Need to validate "is this graph safe for component-based merging?" before architectural commitment.
- Working in ClickHouse (algorithm uses MergeTree + JOIN + GROUP BY only — works on any CH 21.x+).
- Source data has UUID-shaped or string-comparable IDs (the `min(label)` aggregation needs an ordering).

Do NOT use:
- For graphs > ~100M edges (single-server label propagation will be slow; use Spark GraphX or similar).
- When you already know the graph structure (e.g., disjoint groups by construction) — transitive closure is unnecessary.
- For directed graph problems (this assumes undirected — push edges both ways into `_eq_edges`).
