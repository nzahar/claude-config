# ClickHouse Connected Components Diagnostic via Label Propagation

**Extracted:** 2026-05-05
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