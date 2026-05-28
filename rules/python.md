---
paths: ["**/*.py"]
---

## Code Style — Python

### Imports

Strict order: `from __future__ import annotations` → stdlib → third-party → local.
Each group separated by a blank line. Do not use `import *`.

### Type Hints

- Use modern syntax: `dict[str, Any]`, `list[int]`, `str | None` (not `Dict`, `List`, `Optional`)
- `Optional` is acceptable in public function signatures for clarity
- `from __future__ import annotations` — always the first line of the file
- `TYPE_CHECKING` for heavy imports needed only for annotations

### Naming

- `snake_case` for functions and variables
- `_private_prefix` for internal helpers that are not part of the public API
- `UPPER_CASE` for module-level constants
- `_UPPER_CASE` for private constants (e.g. `_CHUNK`, `_UPDATE_COLS`)

### Module Layout

```
from __future__ import annotations
# stdlib
# third-party
# local

CONSTANTS = ...

# ── Section ──────────────────────────────────────

def _helpers():
    ...

def public_functions():
    ...
```

Use `# ── Section ───` em-dash separators for visual grouping in long files.

### Docstrings

- Only for public API and non-obvious functions
- Do not write a docstring if the function name already explains what it does
- Format: brief description + details if needed. No boilerplate `Args:/Returns:` sections unless it is a library

### Error Handling

- FastAPI endpoints: `HTTPException` with a concrete status code and detail
- Background tasks: `try/except Exception` + `logger.exception()` + update status in the DB
- Do not swallow errors silently. Log and update state

### Async

- `asyncio.to_thread()` for sync CPU-heavy calls inside async functions (pandas, openpyxl, file I/O)
- `async with SessionLocal() as session:` — each operation in its own context
- Do not block the event loop

### Formatting

- F-strings for strings. `%s` for logging (`logger.info("msg %s", val)`)
- Line length: aim for <100, but readability matters more than a strict limit
- Comments — only when the code does not explain itself. Do not comment the obvious

### Dataclasses

`@dataclass(frozen=True)` with defaults. Inline comments for non-obvious parameters.

### Python Environment

Before running Python via Bash — determine the path to the right interpreter. Never use `python`, `python3`, `conda run` directly — that gives a system or random env. Always use the absolute path to the project env's interpreter.

**Resolution order:**

1. **Conda env per `environment.yml`.** If the project has `environment.yml`:
   - Env name: `name:` from the YAML.
   - Path: obtain via `conda env list | awk '$1=="<name>"{print $NF}'`. More reliable than guessing the conda install prefix — it varies across machines (`~/miniforge3`, `~/miniconda3`, `~/anaconda3`, `/opt/conda` in the cloud).
   - Binary: `<env-path>/bin/python`.
   - **If `conda` is not installed (cloud runner without conda) or `conda env list` fails / returns empty** — fall through to step 2 immediately, do not retry. The error message does not block the chain.
2. **Project venv.** If `.venv/` or `venv/` is in the root — use `<root>/.venv/bin/python` or `<root>/venv/bin/python`.
3. **Active env as fallback.** If some env is activated (there is `$CONDA_PREFIX` or `$VIRTUAL_ENV`) — use `$CONDA_PREFIX/bin/python` / `$VIRTUAL_ENV/bin/python`.
4. **Otherwise** — ask the user or read the project's `CLAUDE.md`/`README.md` for instructions.

This works locally (macOS/miniforge), in cloud Claude Code, and on Linux servers.
