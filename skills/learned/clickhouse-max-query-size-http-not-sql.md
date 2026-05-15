---
name: ClickHouse max_query_size — pass via HTTP settings, not SQL SETTINGS clause
description: CH parser enforces 256 KiB query limit BEFORE seeing the trailing SETTINGS clause; long IN-lists trip SYNTAX_ERROR (code 62) regardless of `SETTINGS max_query_size = N` in the SQL — pass via clickhouse-connect's HTTP settings parameter instead
type: feedback
---

# ClickHouse max_query_size — pass via HTTP settings, not SQL SETTINGS clause

**Extracted:** 2026-05-14
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
