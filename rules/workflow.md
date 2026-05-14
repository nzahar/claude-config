## Task Workflow — Spec → Plan → Review → Code

For any non-trivial task, follow this sequence strictly:

1. **Agree on the spec** — clarify requirements, constraints, edge cases with the user before planning
2. **Write a visible implementation plan** — markdown file at `docs/plans/<branch-slug>.md` (where `<branch-slug>` is the branch name without the `feature/` or `fix/` prefix). The user can read and edit it; commit it to the repo so the user owns it. Before drafting: identify which modules/areas the work touches, then read `docs/CODEMAPS/<area>.md` for each (focus on meaning-layer blocks) and any ADR in `docs/ADR/` whose Scope covers the affected paths. The plan must reference relevant ADRs explicitly ("respects ADR-NNNN", "supersedes ADR-MMMM"), acknowledge invariants from meaning-layer blocks, and — if the work conflicts with an existing ADR — propose a superseding ADR rather than ignoring the existing one
3. **Get explicit user approval** — wait for the user to confirm the plan before going further
4. **Run `plan-reviewer` on the plan** — six-dimension review (requirement coverage, task completeness, dependency correctness, schema/infra drift, ADR/CODEMAPS compliance, verification plan). The agent returns blockers and warnings; show them to the user. The user (with main session help if needed) decides what to fix. Do not loop with the agent — one report, then decide. Skip this step only for small tasks (see exception below)
5. **Implement step by step** — one logical chunk at a time, not a big-bang generation. When implementing larger features, decompose into independent vertical slices and dispatch parallel subagents

**Step 4.5 — Pre-execution review.** Before running code that touches external resources, performs irreversible writes, or runs an expensive operation, run `code-reviewer` on the code first. Why pre-execution: once you have seen numbers (or stack traces) from a flawed run, confirmation bias is in — the gate must close before results exist. Also, irreversible or external runs cannot be cheaply re-done if a later review catches a problem.

**Default when in doubt: review.** Cost of an unnecessary review is small; cost of an irreversible bad run is high.

**Principle.** Review is required when the next run will (a) touch shared or external resources, (b) make a write that cannot be undone in ~5 minutes, or (c) consume an expensive budget (compute, money, rate limit, wall-clock >~5 min). The lists below are non-exhaustive examples; when an operation is not listed, fall back on the principle.

**Trigger — examples of operations that require review:**

- Connect to any database with production-like data (shared dev, staging, prod, or local snapshot >~10GB), including read-only queries — a bad query can stall a shared cluster or exhaust local resources. "Production-like" is judged by content (real user PII, real business records), not by source label; when unsure, treat as production-like
- DDL or DML on any database, **except** newly-created local containers with no production data
- Network call beyond localhost to a real external service (HTTP API, S3/GCS, MLflow, model registry, etc.) — local mocks (localstack, minio, etc.) do not count
- Installing new dependencies into the active environment (`pip install <new>`, `conda install`, `npm install <new>`); lockfile-driven idempotent restores (`pip install -r requirements.txt` against pinned versions) are exempt
- Training run (GPU usage, `model.fit()`, `optimizer.step()`, explicit `--epochs N`)
- Long-running operation, >~5 min wall clock — judged before launch from intent (full-table scan, full crawl, full training)
- Mass writes to filesystem beyond the project working directory

**Skip review — examples:**

- Pure-read of project-local files (parquet/csv/json under the project tree)
- Unit tests on pure functions, lint, typecheck
- Local in-project ETL (parquet→parquet under the project tree)
- Exploratory iteration on a single notebook cell where the change is below the "substantial rework" bar — the gate fires on substantial rework, not on iteration
- Personal `localhost` sandbox (your own docker, ephemeral, no production snapshot, no other consumers)

**Re-running the same code.** A re-run is exempt if `code-reviewer` already APPROVED this code path on this branch and nothing relevant changed since (query, schema, parameters, dataset, dependency versions, environment variables affecting code path). The pre-merge triad will catch later drift. Verification commands after merge or post-fix that themselves match the trigger (e.g. `alembic upgrade head` against remote DB) are **not** exempt — review first, then run.

**Tie-breaker for "shared" vs "personal" on localhost.** A `localhost` resource counts as shared (→ trigger) if other users / agents / CI depend on its state, or it holds a production snapshot. A truly personal ephemeral sandbox → skip.

**Escape valve.** The user may explicitly override ("skip review, trivial") with three limits:
1. Override is **not** applicable to (a) irreversible writes (DDL/DML on shared/prod, mass deletes, model artifact uploads), or (b) operations that consume a metered or paid budget (rate-limited paid API, GPU-hour billing, etc.). Only to "long-running" and "external read of free/internal resources" categories.
2. If a plan file exists for the branch, the override **must** be recorded there as one line: `YYYY-MM-DD: review skipped for <op>, reason: <user-reason>`. Without the record, the override does not apply.
3. For small tasks without a plan file, override applies only to the "long-running" category — external reads still require review even when small. Irreversible writes and metered-budget operations remain non-overridable.

**Mode selection.** Invoke `code-reviewer mode: research` if the code under review is an experiment notebook OR a training/eval pipeline (file uses `model.fit`, `optimizer.step`, `Trainer`, `--epochs`, or similar), regardless of project-level `default_agent_mode` — artefact type overrides toward research. Research dimensions: leakage/split, baseline/ablation, seed/reproducibility, no-SaaS, no-absolute-paths, provenance. Otherwise invoke `code-reviewer` in default (engineering) mode; focus is on safety of the operation: query plan / index usage, idempotency / rollback for writes, resource consumption for long-running ops.

**Substantial rework (research notebooks).** Use to judge whether a notebook change re-triggers the gate on the same branch:
- Substantial: new training/eval pipeline, new model, changed cohort filter or data split, new external dataset, changed feature engineering, added/removed baseline or ablation, changed seeding / `random_state` handling
- Not substantial: plot styling, markdown edits, variable renames, exploratory cell iteration

One report, then decide — same anti-loop rule as step 4.

For small tasks where a full plan would be overkill: state the approach in one sentence and confirm before coding. Steps 2 and 4 do not apply — there is no plan file to review. Step 4.5 still applies if the small task substantially touches a research notebook.

Never jump straight to code.

## Discipline within long design sessions

Long design sessions (multi-iteration plan-review, ADR drafting, multi-question spec discussions) accumulate conflicting drafts in conversation context. Past a certain length, attention spreads thin and rejected alternatives "resurface" as if current — cognitive degradation that the model cannot reliably self-detect. The rules below counter this with mostly objective triggers (file edits, explicit user phrases, session events) plus a few interpretive ones — distinguishing a confirming "ok" from a conversational "ok", or judging whether a question is design-substantive, still requires reading context. When uncertain, bias toward the action: writing to the plan or re-grounding is cheap, losing a decision is not. Each rule fires independently — there is no "design mode" switch.

| # | Trigger | Action |
|---|---|---|
| 1. **Sub-plan = source of truth** | User confirms a design decision (`ok`, `согласен`, `accepted`, equivalent) on something that belongs in the plan, **and a plan file exists for the current branch** | **Immediately** Edit `docs/plans/<branch-slug>.md` to record the decision, before continuing the conversation. Do not "remember and continue" — written plan is durable, conversation is transient. For small tasks without a plan file (per the small-task exception above) this rule does not fire — do not create a plan file just to satisfy it |
| 2. **Re-grounding at session start** | Start of any session in a git repo | Extends the existing "Project State Awareness" rule in `CLAUDE.md` (which keeps the trivial-edits exception): in addition to `docs/STATE.md`, also read the current branch's plan file (if any) at session start. ADR/CODEMAPS reading still happens when scope is known — not pre-emptively before the user has spoken — same as the existing rule |
| 3. **Discard alternatives in plan** | Editing a plan file, writing a decision section | Plan: **only the current decision**, zero rejected alternatives. ADR: brief mention of rejected approach (risk + revisit trigger), not a parallel implementation. If a rejected option is load-bearing enough to need long-form description — that goes into a future superseding ADR at the moment of revisit, not as preemptive bloat in the current ADR |
| 4. **No branching across two substantive design questions** | User asks Q2 of design-substantive level (requires reasoning + plan record) while Q1 of the same level is unanswered | Close Q1 first by recording in plan, then move to Q2. **Short factual / clarification / yes-no questions batch as usual** — this rule is about parallel design-state, not about being terse |
| 5. **`/compact` ban during design work** | User invokes `/compact` (or asks "compact this conversation") during a session that has done plan / ADR / spec edits or active design discussion | Stop and suggest `/clear` + cold-start from the plan file. **Never** `/compact` — compaction silently loses decision nuance; plan file is durable and re-readable. Trigger on the explicit user invocation, not on self-detected "context bloat" (the model does not see context size as a metric) |

**Session boundaries at phase transitions.** When the plan file marks a phase as done and the next phase is structurally different (design → implementation, implementation → synthesis, design → ADR write-up), suggest the user start a fresh session. Cold-start from STATE.md + plan file is more reliable than dragging accumulated design context into a different mode of work.

These rules apply project-agnostically to any non-trivial task following the spec → plan → review → code workflow above. They do not depend on project type (research vs engineering) or domain.
