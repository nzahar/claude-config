## Task Workflow — Spec → Plan → Review → Code

For any non-trivial task, follow this sequence strictly:

1. **Agree on the spec** — clarify requirements, constraints, edge cases with the user before planning
2. **Write a visible implementation plan** — markdown file at `docs/plans/<branch-slug>.md` (where `<branch-slug>` is the branch name without the `feature/` or `fix/` prefix). The user can read and edit it; commit it to the repo so the user owns it. Before drafting: identify which modules/areas the work touches, then read `docs/CODEMAPS/<area>.md` for each (focus on meaning-layer blocks) and any ADR in `docs/ADR/` whose Scope covers the affected paths. The plan must reference relevant ADRs explicitly ("respects ADR-NNNN", "supersedes ADR-MMMM"), acknowledge invariants from meaning-layer blocks, and — if the work conflicts with an existing ADR — propose a superseding ADR rather than ignoring the existing one
3. **Get explicit user approval** — wait for the user to confirm the plan before going further
4. **Run `plan-reviewer` on the plan** — six-dimension review (requirement coverage, task completeness, dependency correctness, schema/infra drift, ADR/CODEMAPS compliance, verification plan). The agent returns blockers and warnings; show them to the user. The user (with main session help if needed) decides what to fix. Do not loop with the agent — one report, then decide. Skip this step only for small tasks (see exception below)
5. **Implement step by step** — one logical chunk at a time, not a big-bang generation. When implementing larger features, decompose into independent vertical slices and dispatch parallel subagents

**Exception to "no loop" — framework / governance changes** (applies to step 4 plan-reviewer **and** any reviewer cycle whose artifact is a framework document, including `code-reviewer` on a rules/agents diff). When the change under review is itself an edit to a framework / governance document, iterate review→revise with the reviewer until APPROVED with no blockers or warnings (nits OK to ship). A bad framework rule compounds across many future sessions; one extra background-agent pass is cheap by comparison.

**Operational test for "framework-level"** (a change qualifies if a flawed version reliably propagates into future sessions whenever its trigger fires — base-prompt load, agent invocation, slash-command, etc.):

- **Always in scope** (full content loaded every time the trigger fires, trigger fires frequently): `rules/`, `CLAUDE.md`, `agents/`, ADRs — base-prompt auto-load every session for `rules/` and `CLAUDE.md`; full prompt load on every agent invocation for `agents/`
- **In scope on contract changes only** (invoke-on-demand, trigger fires rarely, many edits are prose tweaks): `commands/`, `skills/*` (excluding `learned/`) — iterate when changing **what** the artifact takes/returns or **when** it triggers (description, arguments, output shape, trigger phrasing). Skip iteration for prose tightening, added examples, rationale rewrites
- **Excluded**: `skills/learned/*` (knowledge base, not governance), regular feature work, bugfixes, `workflow.md` §4.5 (operation-level pre-execution review — that gate stays one-shot per code path)

**Loop hygiene.** If iteration extends beyond ~3 cycles, stops converging (each new cycle introduces new warnings from previous fixes — a regression loop, not progress), or context becomes heavy, suggest `/clear` + cold-start from the plan file plus the latest reviewer report. Consistent with design-discipline rule #5 (`/compact` ban during design work).

**Step 4.5 — Pre-execution review.** Before running code that touches external resources, performs irreversible writes, or runs an expensive operation, run `code-reviewer` first. Why pre-execution: once you've seen numbers (or stack traces) from a flawed run, confirmation bias is in — and irreversible / external runs can't be cheaply re-done if review catches a problem later.

**Default when in doubt: review.** Cost of an unnecessary review is small; cost of an irreversible bad run is high.

**Principle.** Review is required when the next run will (a) touch shared or external resources, (b) make a write that cannot be undone in ~5 minutes, or (c) consume an expensive budget (compute, money, rate limit, wall-clock >~5 min). Examples below are non-exhaustive — when an operation is not listed, fall back on the principle.

**Triggers — examples:**

- DB query against production-like data (shared dev, staging, prod, or local snapshot >~10GB), including read-only — a bad query can stall a shared cluster or exhaust local resources. `localhost` counts as shared if other users / agents / CI depend on its state. "Production-like" = real PII or business records, regardless of source label
- DDL or DML on any database, except newly-created local containers with no production data
- Network call beyond localhost to a real external service (HTTP API, S3/GCS, MLflow, model registry); local mocks (localstack, minio) do not count
- New dependency install (`pip install <new>`, `conda install`, `npm install <new>`); lockfile-driven idempotent restores are exempt
- Training run (GPU usage, `model.fit()`, `optimizer.step()`, explicit `--epochs N`)
- Mass writes outside the project tree, or long-running operation (>~5 min wall clock — judged from intent: full-table scan, full crawl, full training)

**Skip — examples:** pure-read of project-local files; unit tests on pure functions, lint, typecheck; local in-project ETL; personal `localhost` sandbox (your own ephemeral docker, no prod snapshot, no other consumers); exploratory iteration on a single notebook cell below the substantial-rework bar (see [`agents/experiment-doc-agent.md`](../agents/experiment-doc-agent.md) "Substantial rework classification").

**Re-running the same code.** A re-run is exempt if `code-reviewer` already APPROVED this code path on this branch and nothing relevant changed since (query, schema, parameters, dataset, dependency versions, environment variables affecting code path). The pre-merge triad catches later drift. Verification commands that themselves match a trigger (e.g. `alembic upgrade head` against remote DB) are **not** exempt — review first, then run.

**Escape valve.** The user may explicitly override ("skip review, trivial") only for "long-running" and "external read of free/internal resources" categories. **Not applicable to** irreversible writes (DDL/DML on shared/prod, mass deletes, artifact uploads) or metered/paid budgets (rate-limited paid API, GPU-hour billing). If a plan file exists for the branch, record the override there: `YYYY-MM-DD: review skipped for <op>, reason: <user-reason>`.

**Mode selection.** Invoke `code-reviewer mode: research` if the code is an experiment notebook or training/eval pipeline (file uses `model.fit`, `optimizer.step`, `Trainer`, `--epochs`, or similar), regardless of project-level `default_agent_mode`. Otherwise invoke in default (engineering) mode.

One report, then decide — same anti-loop rule as step 4.

For small tasks where a full plan would be overkill: state the approach in one sentence and confirm before coding. Steps 2 and 4 do not apply — there is no plan file to review. Step 4.5 still applies if the small task will perform any of the triggering operations above.

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
