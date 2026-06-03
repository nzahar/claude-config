# Global CLAUDE.md

## Language & Communication

- Reply in Russian if I write in Russian, English if English
- Code, commits, PRs, code comments — always English
- Documentation — always English: codemaps (`docs/CODEMAPS/*.md`), ADR (`docs/ADR/*.md`), `STATE.md`, REPORT.md, plans after approval. **Exception**: during the approval stage (workflow step 2–3), `docs/plans/<branch-slug>.md` is written in Russian for reading speed. Immediately after your approval — one translation pass to English; from that point plan-reviewer and the entire downstream work with the English version as canonical. Small tasks without a plan file (small-task exception workflow) do not use this exception — there is no plan and no approval stage.
- Be terse. Do not repeat what I already see in the diff.

## Code-level discipline

- **Comment discipline.** Do not write code comments by default. Before adding any comment, ask: "would removing this confuse a future reader?" If no, cut it. Multi-line comment blocks on a single declaration are nearly always wrong.

## Project State Awareness

**At the start of every session in a project, read `docs/STATE.md` if it exists.** This file is maintained by the project's documentation agent (`document-agent` for engineering projects, `experiment-doc-agent` for research projects; project-level `CLAUDE.md` may declare `state_owner` explicitly). It contains the current trajectory of work: what's blocked, what's planned next, and a history of resolved decisions and cleared blockers — described in terms invariant under merge (PR titles, file-derived statuses), not in terms of branch / working-tree state. "What was just merged" lives in `git log main --merges -1`, not in STATE.md.

Rules:

- **Read it before answering the user's first message.** Not lazily on demand — at session start, alongside (or right after) any other project files you check.
- **Read the `## Current` section.** The `## History` section is for deep context on past trajectory; consult it only if the user asks about prior decisions or you need to understand how the project got here.
- **If the file does not exist, do nothing.** Do not ask the user to create it, do not offer to create it. Some projects don't have one yet, that's fine.
- **STATE.md can be stale.** If the user's first message contradicts what STATE.md treats as currently active or planned (e.g. user opens with "let's work on Y" while STATE.md's `Next up:` says Z) — trust the user. STATE.md describes the project's snapshot at the last documentation pass; it does not bind the user's plans for this session. Note the discrepancy briefly if relevant, do not argue.
- **Never edit STATE.md from the main session.** It is owned by the project's documentation agent (per `state_owner`; default `document-agent` Phase 3 engineering / `experiment-doc-agent` Phase 4 research). Editing it from the main session causes conflicts. If you think STATE.md should be updated, suggest invoking the appropriate documentation agent with `--state-only`.
- **Do not surface STATE.md content unprompted.** Use it for your own orientation. The user does not need a recap of their own project unless they ask for one.

Similarly — when working outside workflow.md (debugging sessions, ad-hoc questions, refactoring without a formal plan), read `docs/CODEMAPS/<area>.md` and relevant ADRs from `docs/ADR/` if the work touches architectural decisions or recorded invariants. For trivial edits (typo, formatting, local bugfix) this is not needed.

## Verification Before Claims

**No completion claim without fresh verification evidence in the current message.**

If you are about to say that tests pass, lint passes, the fix works, the migration ran, the build succeeded, the dependency is installed, the endpoint returns 200, the data loaded, the refactor is equivalent, or anything else of that shape — run the command that proves it *in this message* and include the output (or a concise summary of it).

Evidence from earlier in the session does not count. Output from a previous attempt does not count. "Should work" does not count. Type-check passing is not a substitute for tests passing. Building is not a substitute for running. Running is not a substitute for checking exit code.

If you catch yourself about to write any of these phrases — stop and verify first:
- "should work" / "должно работать"
- "скорее всего работает" / "probably works"
- "теперь должно" / "now it should"
- "по идее" / "in theory"
- "fix should be sufficient" / "фикс должен закрыть"

Run the verification, paste the output, *then* claim.

This applies equally to:
- Implementation work ("I fixed the bug" → run the failing scenario, show it passes)
- Tests ("tests pass" → run them now, show the count)
- Refactors ("behavior preserved" → run the test suite now)
- Infrastructure ("migration applied" → check the schema)
- Dependencies ("installed successfully" → show exit code 0 and the package actually importable)

If the verification is expensive (long test suite, slow build) and you already ran it recently with no intervening changes — say so explicitly: "Tests last ran successfully at [point in conversation]; no code changed since then; I am not re-running." That is an honest exception. Silently skipping verification is not.

If the verification reveals failure — report the failure, do not paper over it with another attempt disguised as a claim.

## Tool Hygiene

**Never use `sed`, `cat`, `head`, `tail`, `awk`, `echo` via Bash for file operations.** In my configuration every such call triggers a permission prompt.

- Reading files (including fragments) — `Read` with `offset`/`limit` parameters. NOT `sed -n 'N,Mp'`, `head -N`, `tail -N`, `cat`.
- Modifying files — `Edit`/`Write`. NOT `sed -i`, NOT `echo > file`, NOT `cat <<EOF > file`.
- Outputting text to the user — direct text in the response. NOT `echo`/`printf` via Bash.

Leave Bash for what `Read`/`Edit`/`Write` cannot do:
- Launching processes (`python`, `npm`, `docker`, `uvicorn`, tests)
- Git (`git status`, `git diff`, `git log`, `git commit`)
- Tree-wide search (`grep -rn`, `find`) — but not for reading found files, only for searching
- Listing directories (`ls`) when the structure is unknown

Rule of thumb: if a specialised tool exists, use it. Bash is the last resort.

## Long-running sub-agents — always in background

**Rule by agent list, not by timer.** Make the foreground/background decision per specific agent, not by a "how many seconds" heuristic.

- **Always background**: `code-reviewer`, `test-writer`, `document-agent`, `experiment-doc-agent`, `Explore` (thorough), `Plan`, `debugger`, `general-purpose` for multi-step tasks. Pre-merge triad (reviewer + test-writer + document-agent) — **always** three parallel background agents in one message.
- **Foreground acceptable**: short targeted requests (Explore quick, targeted grep via general-purpose) where the result is needed for the next step *immediately*. `plan-reviewer` is typically short too — your call, but if the plan is large, launch in background.

Rule of thumb for agents outside the list: if the expected work is longer than ~30 seconds — background.

Why this is the base rule:
1. The agent works in an isolated context — it does not wait for anything from main-session.
2. A foreground agent blocks main-session entirely for 5–15 minutes. The user cannot interrupt without cancelling the whole call. Context is consumed by waiting.
3. Background frees main-session for parallel work + runtime sends a notification on completion. No sleep/poll needed.

When in doubt — background.

## Task Workflow

See [rules/workflow.md](rules/workflow.md).

## Sub-agent Invocation Policy

Sub-agents run in isolated fresh contexts. The unit of review is the **branch** (PR), not the individual commit. Use them fully; full agent contracts live in `agents/*.md`.

### Agent modes

`plan-reviewer` and `code-reviewer` take `mode: engineering | research` in the invocation prompt. Selection: project's `default_agent_mode` (if declared) → structural inference (active `notebooks/<...>/*.ipynb` without `src/` → research; else engineering) → per-branch override (pass explicitly). If a project declares `default_agent_mode: research` and the call lacks `mode:` with no engineering override, the agent errors out — no silent fallback. Other agents (`document-agent`, `experiment-doc-agent`, `test-writer`, `debugger`) have no modes; `experiment-doc-agent` is research-only.

### Project-level `state_owner`

Project's `CLAUDE.md` may declare `state_owner: document-agent | experiment-doc-agent | split`. Default: `document-agent` for engineering (`src/` present, no `notebooks/`), `experiment-doc-agent` for research-only. `split` is for hybrid projects and uses two files: `docs/STATE.md` (engineering, owned by `document-agent`) + `docs/RESEARCH-STATE.md` (research, owned by `experiment-doc-agent`). Never two owners on one file.

### Plan review (`plan-reviewer`)

Trigger — step 4 of `workflow.md`, after the user approves the plan, before any code is written. Mandatory for non-trivial tasks with a plan file at `docs/plans/<branch-slug>.md`. **No loop with the agent** — one report, the user decides what to fix. **Exception** for framework / governance changes (`rules/`, `CLAUDE.md`, `agents/`, ADRs auto-load every session; `commands/` and `skills/*` excluding `learned/` on contract changes only): iterate review→revise until clean (nits OK). See `rules/workflow.md` "Exception to \"no loop\"". The agent finds the plan automatically from the branch — pass an explicit path only if it lives elsewhere. Do not invoke for one-sentence "plans", mid-implementation, or replanning.

### Pre-merge triad (`test-writer` + `code-reviewer` + `document-agent` or `experiment-doc-agent`)

**Scope.** Branch-level gate before merge. Does **not** cover operation-level pre-execution review (`workflow.md` §4.5, auto-detected per-operation). Both gates can fire on the same branch — §4.5 keeps gating operations launched while preparing for merge.

**Trigger — signal from the user**, not auto-detection. Triggers: explicit ("ready to merge", "готовлю к мержу", "прогони проверки"), implicit (the user requests one triad agent but not the others — ask whether to run all three), or `/merge-pr` without prior checks (pause, confirm).

Run all agents in **parallel** in one message — disjoint write targets, no conflicts.

For `document-agent` (engineering or split mode), main-session first decomposes work by codemap:

**Pre-decomposition constraint.** Decomposition runs on committed changes (`git diff main...HEAD`). If there are uncommitted modifications or untracked files relevant to the work — commit them first, otherwise they will not be in scope.

1. `git diff main...HEAD --name-only` — list of changed files in the branch.
2. If `docs/CODEMAPS/` does not exist or is empty — skip decomposition: launch one `document-agent` invocation without scope (full pass) + `--state-only`.
3. For each file: `grep -lF "$file" docs/CODEMAPS/*.md` — which codemaps mention this path. Group `{codemap → [files]}`. Files without a match accumulate into the unmapped-batch.
3.5. **Pre-decompose siblings and pre-declared.** For each file in unmapped-batch:
   - **Sibling proximity:** there is a mapped file in the same directory (exact dirname, not recursive) → move into that codemap's scope.
   - **Pre-declared marker:** mentioned in a codemap as `(planned …)` / `(implementation branch)` / `(future)` / `(deferred)` → move into that codemap's scope.
   - Priority sibling > pre-declared. Ties within the same tier — stays in unmapped-batch.
4. In one message launch in parallel:
   - **N narrow `document-agent` invocations** — one per matched codemap. **Grouping invariant: one codemap appears in exactly one invocation per message.** Each gets an explicit prompt: "Run on `docs/CODEMAPS/<area>.md` with these source files: [list]. Do not touch other codemaps".
   - **+1 unmapped fallback** (if unmapped-batch is non-empty) — one `document-agent` invocation: "these N files are not mentioned in any codemap; decide where to add them or create a new one".
   - **+1 `document-agent --state-only`** — Phase 3, always, in parallel with the others.
   - `code-reviewer` and `test-writer` — as before, in the same message.

If `git diff` is empty or there are no changes in source files — `document-agent` invocations are not launched (only `--state-only` if a session-boundary trigger requires it).

**Reverse-grep false positives — accepted bloat.** `grep -lF "$file"` matches any substring occurrence of a filename in any codemap, including "see also", ADR pointers, prose mentioning neighbouring paths. An extra match → an extra agent call reading that file. Not destructive: the agent sees that the file does not fit its area and makes no edits (or minor ones — a pointer).

For `experiment-doc-agent` (research or split mode), main-session decomposes by experiment:

1. `git diff main...HEAD --name-only` — list of changed files in the branch.
2. Filter paths under `notebooks/<domain>/<file>.ipynb`. If the diff contains only notebook changes — decomposition applies. If there are changes in env-lock / data-manifest / any other non-notebook paths (which trigger drift via mtime in Phase 1) — skip decomposition: one full-pass `experiment-doc-agent` invocation + `--state-only`.
3. For each changed notebook: `grep -lF "<notebook-path>" experiments/*/*/REPORT.md` — find the REPORT.md whose `notebook:` frontmatter points to this path. Group `{experiment → [notebooks]}`. Notebooks without a match are new, without a REPORT.md yet; accumulate them in the unmapped-batch.
3.5. **Pre-decompose siblings and pre-declared.** For each notebook in unmapped-batch:
   - **Sibling proximity:** there is a mapped notebook in the same `notebooks/<domain>/` subfolder → move into that experiment's scope.
   - **Pre-declared marker:** the notebook is mentioned in a REPORT.md as future / planned / related-experiment → move into that experiment's scope.
   - Priority sibling > pre-declared. Ties within the same tier — stays in unmapped-batch.
4. In one message launch in parallel:
   - **N narrow `experiment-doc-agent` invocations** — one per affected experiment. **Grouping invariant**: one experiment appears in exactly one invocation per message. Each gets an explicit prompt: "Run on `experiments/<domain>/<NN_slug>/`. Source notebook: <path>. Do not touch other experiments".
   - **+1 unmapped fallback** (if unmapped-batch is non-empty) — one `experiment-doc-agent` invocation: "these N notebooks have no REPORT.md; create them per the template, place them under `experiments/<domain>/<NN_slug>/`".
   - **+1 `experiment-doc-agent --state-only`** — Phase 4, always, in parallel with the others.

If `git diff` is empty or there are no notebook changes — `experiment-doc-agent` invocations are not launched (only `--state-only` if a session-boundary trigger requires it).

**Split mode safety.** In `state_owner: split` mode, decomposition for document-agent and experiment-doc-agent can run in parallel in one message — write targets disjoint by construction (`docs/CODEMAPS/<area>.md` vs `experiments/<domain>/<NN_slug>/REPORT.md`). STATE.md and RESEARCH-STATE.md are disjoint too.

Expected output: `code-reviewer` verdict (APPROVED / BLOCKED), new test files unstaged, doc/ADR/STATE.md updates unstaged. The user decides how to commit.

### Post-merge documentation agent

Fallback if the triad was skipped and the branch introduced structural changes (routes, schema, models, dependencies, architectural decisions for engineering; new/refreshed experiments for research). Prefer the triad path.

Apply the same scope-decomposition as in the triad. After a squash merge HEAD is already on main, so the diff for the merge-commit changes is `git diff HEAD~1 HEAD --name-only`. Then:
- for `document-agent` — reverse-grep over `docs/CODEMAPS/*.md`;
- for `experiment-doc-agent` — reverse-grep over `experiments/*/*/REPORT.md`.

N narrow invocations + 1 unmapped fallback (if needed) + 1 `--state-only`, all in parallel in one message. If the corresponding directory (`docs/CODEMAPS/` or `experiments/`) does not exist — one full-pass invocation + `--state-only`.

### End-of-session `--state-only`

If a session ends without merge but produced state worth recording (decisions pending, branch active, blockers identified), and the user signals end ("я заканчиваю на сегодня", "stopping for the day", "wrapping up"), invoke the project's documentation agent (`document-agent` or `experiment-doc-agent` per `state_owner`) with `--state-only`. Skip if purely exploratory.

### `debugger` — situational

On-demand when investigation stalls: first fix failed; you can't state the root cause in one mechanistic sentence (`file:line` + mechanism + condition; "probably/maybe" = not a root cause); symptom and cause in different modules; intermittent / timing-dependent; behavior contradicts your model of the code; regression after merge/bump where `git bisect` isn't obvious; user says it's hard. Full exclusion list and root-cause discipline in `agents/debugger.md`.

Calibration signals (weak alone, two or more = trigger): several back-and-forth exchanges without convergence, same file read more than three times, explanations getting longer not shorter, "let me try X" without being able to predict the outcome.

What to pass: exact error, reproduction steps tried (with outcomes), fixes already attempted (with outcomes), relevant file paths. Do NOT pass your hypotheses — the agent isolates from your theory deliberately.

### Mid-branch explicit invocations

Allowed when the user asks, or before a large internal refactor that benefits from a sanity check. Manual, not policy-driven — do not auto-invoke on every intermediate commit.

### Atomicity of commands

Commands (`/commit-push`, `/merge-pr`, others) are atomic — they do exactly what their name says, no more. They do NOT invoke review/test/documentation agents and do NOT edit documentation files (no STATE.md markers, no codemap fixups, no log entries). All quality gates and doc refresh are explicit steps the user or main session runs before/after.

Post-merge STATE.md remains valid: `## Current` is a snapshot describing what's blocked, open questions, and what's next — not in-progress git state, and not the last merge (which lives in `git log`). Routine merges do not require state refresh.

## Git & Workflow

- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`
- One branch per feature: `feature/short-name` or `fix/short-name`
- Squash merge to main via PR
- Do not push secrets. Use `.env` + `.env.example`
- **NEVER run `git commit`, `git push`, `docker push`, or invoke commands `/ship`, `/commit-push`, `/merge-pr` (and their direct equivalents `gh pr create`, `gh pr merge`, MCP analogs `mcp__github__create_pull_request`, `mcp__github__merge_pull_request`) without an explicit user request.** Implementing a task does not imply automatic commit, publication, or merge. After implementation (including code-review and applying nits) — **stop and wait for an explicit command**. Trigger words allowing the shipping phase: «коммить» / «закоммить» / «commit», «push» / «запушь», «/ship» / «шипай», «/commit-push», «/merge-pr <N>», «merge», «открой PR» / «open PR». Ambiguity ("сделай", "имплементируй", "продолжай", "do", "implement", "continue") is interpreted conservatively — code-level edits only, no commit/push. Docker images can be built locally (`docker build`), but pushing to a registry — only on an explicit command.

## Stack Preferences

- **Python 3.12**, conda for envs (`environment.yml`)
- **FastAPI** + `uvicorn` (async, lifespan context manager)
- **Go** for performance-critical services
- **React** + **TypeScript** for the frontend
- **PostgreSQL** + `asyncpg` + **SQLAlchemy 2.x** async (Python) / `pgx` (Go)
- **Alembic** for migrations (Python), `golang-migrate` (Go)
- **pandas** for data processing
- **Docker Compose** for infrastructure

## Library Documentation

For questions about libraries / frameworks / SDKs / CLIs (API syntax, configuration, version migrations, library-specific debugging) prefer **context7 MCP** (`mcp__plugin_context7_context7__resolve-library-id` → `query-docs`) over training data and WebSearch. Do not use for refactoring, general programming concepts, or debugging business logic.
