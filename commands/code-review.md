# Code Review

Comprehensive security and quality review of uncommitted changes or open PR.
If there are no changed files (git diff --name-only HEAD) — check open PRs using gh.
If there are multiple open PRs — ask user which one to review.

## 1. Get changed files

- `git diff --name-only HEAD` for uncommitted changes
- `gh pr diff <N> --name-only` for PR review

## 2. Check each file

### Universal (any language) — CRITICAL:
- Hardcoded credentials, API keys, tokens, passwords
- SQL injection vulnerabilities
- Path traversal risks (user input in file paths)
- Missing input validation on API boundaries
- Secrets in committed files (.env, private keys)

### Universal — HIGH:
- Functions > 50 lines
- Files > 800 lines
- Nesting depth > 4 levels
- Missing error handling (bare except, ignored errors)
- TODO/FIXME comments without a ticket reference

### Python-specific:
- `print()` instead of `logging`
- Blocking sync calls inside async functions (missing `asyncio.to_thread()`)
- `str(x) != "nan"` instead of `pd.isna()` / `math.isnan()`
- Missing type hints on public function signatures
- Mutable default arguments (`def f(x=[])`)

### Go-specific:
- Unchecked `error` return values
- Goroutine without cancellation mechanism (context, done channel)
- `defer` inside a loop
- `panic()` in business logic (not init/main)
- Unexported fields in structs used for JSON marshal
- Missing `context.Context` propagation in handlers

### React/JS/TS-specific:
- `console.log` left in code
- React hooks called conditionally or inside loops
- Missing `key` prop in list rendering
- Direct state mutation (not using setState/dispatch)
- `any` type in TypeScript without justification
- Missing `alt` on images, `aria-label` on icon buttons
- Missing JSDoc/TSDoc on exported components and hooks

### Best Practices — MEDIUM:
- Missing tests for new code
- Dead code (unused imports, unreachable branches)

## 3. Generate report

For each issue:
- Severity: CRITICAL, HIGH, MEDIUM, LOW
- File path and line number
- Issue description
- Suggested fix

## 4. Verdict

- **BLOCKED** if any CRITICAL or HIGH issues found — list what must be fixed
- **APPROVED** if only MEDIUM/LOW remain
