## Task Workflow — Spec → Plan → Review → Code

Every task starts with track selection at intake. The numbered sequence below is the **full track**; the **light track** is the default.

**Track selection (intake).** Cheap read-only scouting first — grep, Read, an `Explore` agent — until the change is enumerable; if a `docs/ADR/*` Scope covers a touched path, read that ADR before judging trigger 3. Then full track iff at least one positive trigger holds:

1. a §4.5-class operation (irreversible write, external resource, expensive run) is part of the task itself, not of its verification;
2. a public contract change — DB schema / migration, API endpoint, wire format, CLI arguments;
3. a design fork that one question to the user cannot close — anything Discipline rule 1 would require recording in a plan, including a change that violates or supersedes an ADR invariant (→ superseding ADR, step 2);
4. the user asks for a plan;
5. the work is still not enumerable after scouting — open-ended exploration, exploratory notebook work ("try and see").

Otherwise light track, regardless of diff size — file count and module count are not criteria. Framework edits (`rules/`, `CLAUDE.md`, `agents/`, `skills/`) use the same test: clarifying an existing rule with no fork → light; a new rule, gate, agent or skill contract is almost always a fork → full.

**Light track.** Publish a declaration: one sentence of approach + the file list from scouting + optionally a 3–7-line mini-plan of steps, inline in the message. No plan file, no `plan-reviewer`; a decision closed by one exchange with the user is recorded in the commit body. Work starts immediately — the user sees the declaration and can interrupt. The file list is for transparency: a file discovered later is appended to it — not by itself an escalation.

Tripwires — either one fires → mandatory escalation to the full track:

- (a) the second fix attempt failed, or `debugger` — invoked after the first failure, still on the light track — cannot state the root cause in one mechanistic sentence;
- (b) a fork surfaced that one exchange with the user did not close, or an intake trigger turns out to hold after all.

The ratchet is one-way: light → full at any moment; full → light mid-task — never. Escalation keeps the working tree: write a plan for the remaining work, recording decisions already made, then continue on the full track from step 2.

End of a light-track task: commit and push. The pre-merge triad is **not** auto-dispatched — a light-track task routinely lands mid-session with no merge in sight, and the triad is a branch-level pre-merge gate, not a task-level one. It fires on the same trigger as on the full track: the one defined in CLAUDE.md §Pre-merge triad.

Unchanged on the light track: §4.5 pre-execution review, Verification Before Claims, PR/merge gates, conventional commits, one branch per feature. Tripwires and §4.5 are orthogonal axes: a §4.5 trigger fires the one-shot operation review, not a track switch. Exploratory notebook work is trigger 5 — no separate research variant.

**Full track:**

1. **Agree on the spec** — clarify requirements, constraints, edge cases with the user before planning
2. **Write a visible implementation plan** — markdown file at `docs/plans/<branch-slug>.md` (where `<branch-slug>` is the branch name without the `feature/` or `fix/` prefix). The user can read and edit it; commit it to the repo so the user owns it. Before drafting: identify which modules/areas the work touches, then read `docs/CODEMAPS/<area>.md` for each (focus on meaning-layer blocks) and any ADR in `docs/ADR/` whose Scope covers the affected paths. The plan must reference relevant ADRs explicitly ("respects ADR-NNNN", "supersedes ADR-MMMM"), acknowledge invariants from meaning-layer blocks, and — if the work conflicts with an existing ADR — propose a superseding ADR rather than ignoring the existing one. Three authoring rules bind the plan text: **No claim without evidence** — a statement about code or data carries `file:line`, or one line with the result of an executed read-only probe. **No risk without evidence** — a gate, step or fallback for a risk earns its place only when a named instance exists (measurement, incident, `file:line`, codemap block); a hypothetical risk gets one line or is cut (§Documentation economy). **Zero growth on revision** — a revised draft stays ≤ previous draft + 10 % LOC; revisions replace text, they do not append (this is the SSOT for zero growth; §Discipline rule 6 points here). Probes are project-local reads and greps by default; a probe that matches a §4.5 trigger goes through §4.5 first
3. **Get explicit user approval** — wait for the user to confirm the plan before going further
4. **Run `plan-reviewer` on the plan — one round.** Six-dimension review (requirement coverage, task completeness, dependency correctness, schema/infra drift, ADR/CODEMAPS compliance, verification plan). The agent returns one report; show it to the user. Skip this step only on the light track (no plan file exists)
   - **A blocker names an irreversible cost** — data lost, money spent, compute burned, wrong output reaching a user — and the moment in the plan where it lands before any signal catches it; a finding without such a cost is a warning (the definition is SSOT in `agents/plan-reviewer.md`). **Blockers are fixed into the plan before implementation starts**; warnings the main session fixes inline where it agrees and states what it declined. Then implement — like §4.5, this review is one-shot per draft
   - **Re-review only on explicit user request.** No automatic second round. When the user asks for one, the prompt names the previous report and the fixes made; the agent runs the scoped pass defined in `agents/plan-reviewer.md` § Re-review. Framework / governance plans follow the same rule
5. **Implement step by step** — one logical chunk at a time, not a big-bang generation

**Step 4.5 — Pre-execution review.** Before running code that touches external resources, performs irreversible writes, or runs an expensive operation, run `code-reviewer` first.

**Default when in doubt: review.**

**Principle.** Review is required when the next run will (a) touch shared or external resources, (b) make a write that cannot be undone in ~5 minutes, or (c) consume an expensive budget (compute, money, rate limit, wall-clock >~5 min). Examples below are non-exhaustive — when an operation is not listed, fall back on the principle.

**Triggers — examples:**

- DB query against production-like data (shared dev, staging, prod, or local snapshot >~10GB), including read-only. `localhost` counts as shared if other users / agents / CI depend on its state. "Production-like" = real PII or business records, regardless of source label
- DDL or DML on any database, except newly-created local containers with no production data
- Network call beyond localhost to a real external service (HTTP API, S3/GCS, MLflow, model registry); local mocks (localstack, minio) do not count
- Training run (GPU usage, `model.fit()`, `optimizer.step()`, explicit `--epochs N`)
- Mass writes outside the project tree, or long-running operation (>~5 min wall clock — judged from intent: full-table scan, full crawl, full training)

**Skip — examples:** pure-read of project-local files; unit tests on pure functions, lint, typecheck; local in-project ETL; personal `localhost` sandbox (your own ephemeral docker, no prod snapshot, no other consumers); exploratory iteration on a single notebook cell below the substantial-rework bar (see [`agents/experiment-doc-agent.md`](../agents/experiment-doc-agent.md) "Substantial rework classification").

**Re-running the same code.** A re-run is exempt if `code-reviewer` already APPROVED this code path on this branch and nothing relevant changed since (query, schema, parameters, dataset, dependency versions, environment variables affecting code path). The pre-merge triad catches later drift. Verification commands that themselves match a trigger (e.g. `alembic upgrade head` against remote DB) are **not** exempt — review first, then run.

**Escape valve.** The user may explicitly override ("skip review, trivial") only for "long-running" and "external read of free/internal resources" categories. **Not applicable to** irreversible writes (DDL/DML on shared/prod, mass deletes, artifact uploads) or metered/paid budgets (rate-limited paid API, GPU-hour billing). **For light-track tasks**, override applies only to the "long-running" category — external reads still require review.

**Mode selection.** Invoke `code-reviewer mode: research` if the code is an experiment notebook or training/eval pipeline (file uses `model.fit`, `optimizer.step`, `Trainer`, `--epochs`, or similar), regardless of project-level `default_agent_mode`. Otherwise invoke in default (engineering) mode.

One report, then decide — §4.5 is one-shot per code path, not a 2-round mini-loop.

Never start code before the intake declaration (light track) or an approved plan that has cleared plan review (full track).

## Discipline within long design sessions

Long design sessions (plan revision after review, ADR drafting, multi-question spec discussions) accumulate conflicting drafts in conversation context. The rules below counter this with mostly objective triggers (file edits, explicit user phrases, session events) plus a few interpretive ones that still require reading context. When uncertain, bias toward the action. Each rule fires independently — there is no "design mode" switch.

| # | Trigger | Action |
|---|---|---|
| 1. **Sub-plan = source of truth** | User confirms a design decision (`ok`, `согласен`, `accepted`, equivalent) on something that belongs in the plan, **and a plan file exists for the current branch** | **Immediately** Edit `docs/plans/<branch-slug>.md` to record the decision, before continuing the conversation. Do not "remember and continue" — written plan is durable, conversation is transient. On the light track this rule does not fire — a fork that one exchange with the user did not close is intake trigger 3 / tripwire (b) and escalates to the full track |
| 2. **Re-grounding at session start** | Start of any session in a git repo | Extends `CLAUDE.md` §Roadmap — in addition to `docs/ROADMAP.md` (`## Now`; plus `## Next` per the empty-`## Now` rule), also read the current branch's plan file at `docs/plans/<branch-slug>.md` if it exists. The base rule's trivial-edits exception and the scope-known ADR/CODEMAPS rule continue to apply |
| 3. **Discard alternatives in plan** | Editing a plan file, writing a decision section | Plan: **only the current decision**, zero rejected alternatives. ADR: brief mention of rejected approach (risk + revisit trigger), not a parallel implementation. If a rejected option is load-bearing enough to need long-form description — that goes into a future superseding ADR at the moment of revisit, not as preemptive bloat in the current ADR |
| 4. **No branching across two substantive design questions** | User asks Q2 of design-substantive level (requires reasoning + plan record) while Q1 of the same level is unanswered | Close Q1 first by recording in plan, then move to Q2. **Short factual / clarification / yes-no questions batch as usual** — this rule is about parallel design-state, not about being terse |
| 5. **`/compact` ban during design work** | User invokes `/compact` (or asks "compact this conversation") during a session that has done plan / ADR / spec edits or active design discussion | Stop and suggest `/clear` + cold-start from the plan file. **Never** `/compact` — compaction silently loses decision nuance. Trigger on the explicit user invocation, not on self-detected "context bloat" |
| 6. **Plan size soft trigger (non-framework)** | Non-framework plan (framework = edits to `rules/`, `CLAUDE.md`, `agents/`, `skills/` per intake) in `plans/` grows past ~200 LOC during revision | Explicit refactor pass before the revised plan goes back to the user or implementation starts. Soft signal, not hard cap — defensive bloat is the typical cause; legitimate multi-system plans may exceed 200 LOC. Per-revision growth is bounded separately by the step-2 zero-growth rule (≤ +10 % LOC per revision) |

**Session boundaries at phase transitions.** When the plan file marks a phase as done and the next phase is structurally different (design → implementation, implementation → synthesis, design → ADR write-up), suggest the user start a fresh session.

These rules apply project-agnostically to any full-track task following the spec → plan → review → code workflow above.

## Documentation economy

Rules for whoever writes a plan, an ADR, a codemap or a REPORT.md. Reviewers apply them as ordinary judgment under their own finding rules; there is no detection procedure and no severity table.

- A plan holds the contract and the steps, not the implementation: no function or class bodies, a signature line at most.
- A plan closes every question in its Decisions table before review, or marks it `deferred to implementation: <trigger>`.
- A step, gate or fallback that guards a risk names the evidence for that risk — a measurement, an incident, a `file:line`. Without it: one line, or nothing.
- A plan does not copy its Decisions table into an ADR outline; a pointer is enough.
- An ADR is one decision. If the trigger to revisit one decision does not touch another, they are separate ADRs. Its alternatives are only those genuinely weighed.
- A cross-reference replaces content, it does not accompany it. A document reaching for a fifth pointer per hundred lines needs trimming, not the pointer.
- A table cell holds at most three statements. Longer content is prose or is cut.
