## Task Workflow — Spec → Plan → Review → Code

For any non-trivial task, follow this sequence strictly:

1. **Agree on the spec** — clarify requirements, constraints, edge cases with the user before planning
2. **Write a visible implementation plan** — markdown file at `docs/plans/<branch-slug>.md` (where `<branch-slug>` is the branch name without the `feature/` or `fix/` prefix). The user can read and edit it; commit it to the repo so the user owns it. Before drafting: identify which modules/areas the work touches, then read `docs/CODEMAPS/<area>.md` for each (focus on meaning-layer blocks) and any ADR in `docs/ADR/` whose Scope covers the affected paths. The plan must reference relevant ADRs explicitly ("respects ADR-NNNN", "supersedes ADR-MMMM"), acknowledge invariants from meaning-layer blocks, and — if the work conflicts with an existing ADR — propose a superseding ADR rather than ignoring the existing one
3. **Get explicit user approval** — wait for the user to confirm the plan before going further
4. **Run `plan-reviewer` on the plan** — seven-dimension review (requirement coverage, task completeness, dependency correctness, schema/infra drift, ADR/CODEMAPS compliance, verification plan, documentation economy). The agent returns blockers and warnings; show them to the user. The user (with main session help if needed) decides what to fix. **A report with blockers never authorizes implementation. Fix them and run another round within the cap below; if the cap is exhausted with blockers still open, the exit is scrap-and-rewrite, not implementation.** Hard cap: 2 reviewer invocations on the same draft for non-framework plans. After round 2 either accept-warnings or scrap-and-rewrite — never invoke for round 3 on the same draft. Skip this step only for small tasks (see exception below)
5. **Implement step by step** — one logical chunk at a time, not a big-bang generation. When implementing larger features, decompose into independent vertical slices and dispatch parallel subagents

**Exception to "no loop" — framework / governance changes** (applies to step 4 plan-reviewer **and** any reviewer cycle whose artifact is a framework document, including `code-reviewer` on a rules/agents diff). When the change under review is itself an edit to a framework / governance document, iterate review→revise with the reviewer until APPROVED with no blockers or warnings (nits OK to ship).

**Framework hard cap: 3 reviewer invocations on the same draft.** After round 3, choose one explicitly — ship with remaining warnings (nits, taste-level), scrap-and-cold-start (`/clear`, rewrite from plan + last reviewer report — counts as a new cycle, not a continuation), or decompose (split one artifact into multiple — typically rule + ADR, or two narrower rules). Never invoke reviewer for round 4 on the same draft.

**Counting.** "Round" counts only formal reviewer invocations (`plan-reviewer`, `code-reviewer`) on the same draft. Both reviewers share the same counter when applied to the same artifact. Conversation with the user does not count toward the cap. "Same draft" = the artifact carried forward across reviewer rounds: edits made in response to the previous round's findings, including structural revisions, stay the same draft and do not reset the counter. Only `/clear` + cold-start rewrite from the plan file plus last reviewer report produces a new draft with a fresh counter — that is the intended escape valve for "scrap and cold-start", not a loophole to reset the counter on the same exhausted draft.

**Smoke beats review on data work.** This applies to the step 4 / framework `plan-reviewer` loops above — not to §4.5 pre-execution review (which is one-shot per code path). For changes that touch data per the §4.5 trigger list (principle and examples there — wide reading on purpose, includes operations that match the principle but no enumerated trigger): when the cap is exhausted with remaining warnings, running smoke against real data is an additional exit option alongside the listed alternatives in each cap branch (non-framework cap=2: accept-warnings, scrap-and-rewrite; framework cap=3: ship-with-warnings, scrap-and-cold-start, decompose).

**Operational test for "framework-level"** (a change qualifies if a flawed version reliably propagates into future sessions whenever its trigger fires — base-prompt load, agent invocation, slash-command, etc.):

- **Always in scope** (full content loaded every time the trigger fires, trigger fires frequently): `rules/`, `CLAUDE.md`, `agents/`, ADRs — base-prompt auto-load every session for `rules/` and `CLAUDE.md`; full prompt load on every agent invocation for `agents/`
- **In scope on contract changes only** (invoke-on-demand, trigger fires rarely, many edits are prose tweaks): `commands/`, `skills/*` (excluding `learned/`) — iterate when changing **what** the artifact takes/returns or **when** it triggers (description, arguments, output shape, trigger phrasing). Skip iteration for prose tightening, added examples, rationale rewrites
- **Excluded**: `skills/learned/*` (knowledge base, not governance), regular feature work, bugfixes, `workflow.md` §4.5 (operation-level pre-execution review — that gate stays one-shot per code path)

**Loop hygiene.** If iteration extends beyond ~3 cycles, stops converging (each new cycle introduces new warnings from previous fixes — a regression loop, not progress), or context becomes heavy, suggest `/clear` + cold-start from the plan file plus the latest reviewer report. Consistent with design-discipline rule #5 (`/compact` ban during design work).

**Step 4.5 — Pre-execution review.** Before running code that touches external resources, performs irreversible writes, or runs an expensive operation, run `code-reviewer` first.

**Default when in doubt: review.**

**Principle.** Review is required when the next run will (a) touch shared or external resources, (b) make a write that cannot be undone in ~5 minutes, or (c) consume an expensive budget (compute, money, rate limit, wall-clock >~5 min). Examples below are non-exhaustive — when an operation is not listed, fall back on the principle.

**Triggers — examples:**

- DB query against production-like data (shared dev, staging, prod, or local snapshot >~10GB), including read-only. `localhost` counts as shared if other users / agents / CI depend on its state. "Production-like" = real PII or business records, regardless of source label
- DDL or DML on any database, except newly-created local containers with no production data
- Network call beyond localhost to a real external service (HTTP API, S3/GCS, MLflow, model registry); local mocks (localstack, minio) do not count
- New dependency install (`pip install <new>`, `conda install`, `npm install <new>`); lockfile-driven idempotent restores are exempt
- Training run (GPU usage, `model.fit()`, `optimizer.step()`, explicit `--epochs N`)
- Mass writes outside the project tree, or long-running operation (>~5 min wall clock — judged from intent: full-table scan, full crawl, full training)

**Skip — examples:** pure-read of project-local files; unit tests on pure functions, lint, typecheck; local in-project ETL; personal `localhost` sandbox (your own ephemeral docker, no prod snapshot, no other consumers); exploratory iteration on a single notebook cell below the substantial-rework bar (see [`agents/experiment-doc-agent.md`](../agents/experiment-doc-agent.md) "Substantial rework classification").

**Re-running the same code.** A re-run is exempt if `code-reviewer` already APPROVED this code path on this branch and nothing relevant changed since (query, schema, parameters, dataset, dependency versions, environment variables affecting code path). The pre-merge triad catches later drift. Verification commands that themselves match a trigger (e.g. `alembic upgrade head` against remote DB) are **not** exempt — review first, then run.

**Escape valve.** The user may explicitly override ("skip review, trivial") only for "long-running" and "external read of free/internal resources" categories. **Not applicable to** irreversible writes (DDL/DML on shared/prod, mass deletes, artifact uploads) or metered/paid budgets (rate-limited paid API, GPU-hour billing). **For small tasks without a plan file**, override applies only to the "long-running" category — external reads still require review.

**Mode selection.** Invoke `code-reviewer mode: research` if the code is an experiment notebook or training/eval pipeline (file uses `model.fit`, `optimizer.step`, `Trainer`, `--epochs`, or similar), regardless of project-level `default_agent_mode`. Otherwise invoke in default (engineering) mode.

One report, then decide — §4.5 is one-shot per code path, not a 2-round mini-loop.

For small tasks where a full plan would be overkill: state the approach in one sentence and confirm before coding. Steps 2 and 4 do not apply — there is no plan file to review. Step 4.5 still applies if the small task will perform any of the triggering operations above.

Never jump straight to code.

## Discipline within long design sessions

Long design sessions (multi-iteration plan-review, ADR drafting, multi-question spec discussions) accumulate conflicting drafts in conversation context. The rules below counter this with mostly objective triggers (file edits, explicit user phrases, session events) plus a few interpretive ones that still require reading context. When uncertain, bias toward the action. Each rule fires independently — there is no "design mode" switch.

| # | Trigger | Action |
|---|---|---|
| 1. **Sub-plan = source of truth** | User confirms a design decision (`ok`, `согласен`, `accepted`, equivalent) on something that belongs in the plan, **and a plan file exists for the current branch** | **Immediately** Edit `docs/plans/<branch-slug>.md` to record the decision, before continuing the conversation. Do not "remember and continue" — written plan is durable, conversation is transient. For small tasks without a plan file (per the small-task exception above) this rule does not fire — do not create a plan file just to satisfy it |
| 2. **Re-grounding at session start** | Start of any session in a git repo | Extends `CLAUDE.md` §"Project State Awareness" — in addition to `docs/STATE.md`, also read the current branch's plan file at `docs/plans/<branch-slug>.md` if it exists. The base rule's trivial-edits exception and the scope-known ADR/CODEMAPS rule continue to apply |
| 3. **Discard alternatives in plan** | Editing a plan file, writing a decision section | Plan: **only the current decision**, zero rejected alternatives. ADR: brief mention of rejected approach (risk + revisit trigger), not a parallel implementation. If a rejected option is load-bearing enough to need long-form description — that goes into a future superseding ADR at the moment of revisit, not as preemptive bloat in the current ADR |
| 4. **No branching across two substantive design questions** | User asks Q2 of design-substantive level (requires reasoning + plan record) while Q1 of the same level is unanswered | Close Q1 first by recording in plan, then move to Q2. **Short factual / clarification / yes-no questions batch as usual** — this rule is about parallel design-state, not about being terse |
| 5. **`/compact` ban during design work** | User invokes `/compact` (or asks "compact this conversation") during a session that has done plan / ADR / spec edits or active design discussion | Stop and suggest `/clear` + cold-start from the plan file. **Never** `/compact` — compaction silently loses decision nuance. Trigger on the explicit user invocation, not on self-detected "context bloat" |
| 6. **Plan size soft trigger (non-framework)** | Non-framework plan in `plans/` grows past ~200 LOC during revision | Explicit refactor pass before next reviewer invocation. Soft signal, not hard cap — defensive bloat is the typical cause; legitimate multi-system plans may exceed 200 LOC |

**Session boundaries at phase transitions.** When the plan file marks a phase as done and the next phase is structurally different (design → implementation, implementation → synthesis, design → ADR write-up), suggest the user start a fresh session.

These rules apply project-agnostically to any non-trivial task following the spec → plan → review → code workflow above.

## Documentation economy

Documentation written by main-session (plans, ADRs) and by documentation agents (codemaps, STATE, REPORT.md) tends to accumulate bloat: inline implementation in plans, duplicated symbol tables in codemaps, defensive cross-references, strawman alternatives in ADRs, duplicate STATE entries. The rules below codify what counts as bloat and how reviewer agents detect it. Each rule has both an **authoring constraint** (what whoever writes the artifact must not produce) and a mechanical **detection procedure** (what the reviewer agent mechanically checks). Both sides reference the same threshold.

- **D1. Plan documents contract + steps, not implementation.** Inline function/class body > 5 lines in `docs/plans/*.md` = signal scope creep. Signature snippets (1–3 lines) for fixing API contract are acceptable.
  - _Authoring:_ Do not paste function or class bodies into `docs/plans/*.md`. Limit code blocks to signature snippets of 1–3 lines that fix an API contract. If you reach for a 6+ line implementation, link to the file or describe the contract in prose instead.
  - _Detection:_ for each fenced code block (` ``` ` … ` ``` `) in any file under `docs/plans/` — count consecutive non-empty lines inside. > 5 → 1 finding per block. Inline `code` (single backticks) does not count.

- **D2. Plan does not duplicate ADR-outline.** If the Decisions table fixes decisions for a future ADR, a separate "ADR-XXXX outline" section is a pointer (Q-number → D-number), not a content duplicate.
  - _Authoring:_ Do not duplicate a Decisions table into an `## ADR-XXXX outline` section. Keep the outline, if present, as a pointer table (Q-number → D-number), not a content copy.
  - _Detection:_ if a plan contains a section heading matching `^## ADR-` **and** a Decisions table, compare content of Decision cells in the table against the bullets in the outline section. > 50% overlap → 1 finding for the entire outline section.

- **D3. ADR = one thematically coherent cluster.** Operational test: if the revisit-trigger of one decision does not affect the others → they belong in separate ADRs.
  - _Authoring:_ Group decisions in an ADR by thematic coherence. If the revisit-trigger of one decision does not affect the others, split into separate ADRs. Split before writing further when sub-headings exceed 8 `### Dn` items.
  - _Detection:_ count sub-headings matching `^### D[0-9]+` or `^### D[A-Z]` in the ADR. > 8 → 1 finding (signal multi-ADR). Reviewer additionally verifies revisit-trigger independence: if "Revisit triggers" addresses only a subset of D-numbers without cross-refs between them, confirms split candidate.

- **D4. ADR "Alternatives considered" section lists only alternatives that were genuinely weighed.** Strawman (rejected at write-time without serious consideration) is out.
  - _Authoring:_ List only genuinely-weighed options in an ADR §Alternatives section. Cut any alternative whose only Cons line is a dismissive clause without quantitative or structural reasoning ("breaks symmetry", "overkill", "no use case") — that is a strawman.
  - _Detection:_ heuristic. Flag an alternative as strawman if its Cons/"Минусы" description is a single dismissive clause without quantitative or structural reasoning (e.g., "breaks symmetry", "overkill", "no use case" without naming the assessment basis). 1 finding per detected strawman.

- **D5. Plan-reviewer does not accept a plan with open questions in §Decisions.** Open questions are closed before approval or explicitly marked `deferred to implementation: <trigger>`.
  - _Authoring:_ Close every open question in §Decisions before sending a plan to `plan-reviewer`, or explicitly mark it `deferred to implementation: <trigger>` with a concrete trigger. Do not leave `TBD`, «нужно решить», or equivalent in the Decision/Why columns of the Decisions table.
  - _Detection:_ grep within `## Decisions` (Decision/Why columns only — **not** the Question column) and `## Open questions` body sections for textual tokens: `TBD`, `tbd`, «нужно решить», «not decided», «to be decided». > 0 without an explicit `deferred to implementation: <trigger>` qualifier → 1 finding per occurrence. **Do not use `?` as a token** — it collides with legitimate Question column entries. **Do not use «open question» as a token** — that phrase frequently appears legitimately in self-reference / prose.

- **D6. Cross-references like «see ADR-NNNN», «see §DM» in prose body of `docs/plans/*.md` and `docs/ADR/*.md` are capped at ≤ 4 per 100 LOC.** Exceeding = signal that the doc needs trimming.
  - _Authoring:_ Cap cross-references ("see ADR-NNNN", «см. ADR-NNNN», "see §Dn") in plan and ADR prose at ≤ 4 per 100 LOC. If you reach for the fifth, the doc needs trimming, not another pointer. Scope exclusions (codemaps, Decisions-table cells) per Scope block below.
  - _Scope:_ **only** `docs/plans/*.md` and `docs/ADR/*.md`. **Does not apply to codemaps** — there cross-refs are the primary anchoring mechanism of the meaning layer, not bloat. **Does not apply to `## Decisions` table cells** — Why-column reasoning legitimately cites ADRs/sections for justification; a compact table is not bloat.
  - _Detection:_ regex `(see ADR-\d+|см\. ADR-\d+|см\. §D\d+|see §D\d+)` over body, excluding (a) fenced code blocks, (b) markdown table rows (`|...|`). Ratio = matches / (LOC/100). > 4.0 → 1 WARNING for the entire file. Threshold calibrated on observation that framework plans legitimately require 3–5 anchoring references per 100 LOC.

- **D7. Markdown table cell length: one cell ≤ 3 independent statements.** Lyrical expansions ("in practice X but Y…") go to a separate § Notes or get cut.
  - _Authoring:_ Keep markdown table cells to ≤ 3 independent statements. Move lyrical expansions ("in practice X but Y…") to a separate §Notes or cut them. Em-dash parenthetical pauses inside a single statement do not count as additional statements. **For codemap Files-table cells and REPORT.md table cells specifically**, an additional mechanical **primary budget of ≤ 200 chars per cell** applies (idempotent, false-positive-resistant); the ≤ 3-statement rule is the secondary content-shape check there. Over-budget cell prose is **relocated verbatim** into the meaning/results layer per [`lib/doc-compaction-contract.md`](../lib/doc-compaction-contract.md), never truncated.
  - _Detection:_ for each cell in a `|...|...|` row — count sentences (split on `. ` or `; `). > 3 → 1 finding per cell. Code-fenced content inside a cell does not count. **Note:** ` — ` (em-dash with surrounding spaces) is deliberately **not** a split delimiter — it is widely used as a stylistic parenthetical pause in this codebase, and splitting on it inflates the count on legitimate prose. **For cells in `docs/CODEMAPS/*.md` and `*/REPORT.md`**, additionally flag any cell whose content exceeds 200 chars (excluding surrounding pipes/spaces) — 1 finding per cell; this is the primary check for those two artifacts.

- **D8. Codemap / REPORT.md size hard-cap.** `docs/CODEMAPS/*.md` and `REPORT.md` files are capped on their structural portion (total lines minus the protected meaning-layer / results blocks); an over-cap file is compacted by the owning doc agent. SSOT for the threshold, the compaction procedure, and the structural-portion definition is [`lib/doc-compaction-contract.md`](../lib/doc-compaction-contract.md) — do not restate the value here.
  - _Authoring:_ The owning doc agent (`document-agent` Phase 1 / `experiment-doc-agent` Phase 1) keeps the structural portion under the hard cap by running the size-triggered compaction defined in the contract. The protected block is never counted or compacted; relocation is verbatim (move-not-edit).
  - _Detection:_ a `code-reviewer` line-count tripwire — when a diff touches `docs/CODEMAPS/*.md` or `*/REPORT.md` and the resulting file's structural portion exceeds the hard cap, emit ONE informational (LOW) finding "over size cap — document-agent compaction owed". This is a line-count on a file already read for the diff, **not** a whole-file review, and is **not** blocking (compaction may be in flight in the parallel pre-merge triad).
  - _Scope:_ this rule is the discoverability pointer; the owning doc agent (not the reviewer) is the enforcement actor. Threshold and procedure are SSOT'd in the contract, not duplicated here.

**Application across agents.** Detection procedures above are the single source of truth. Reviewer agents (`plan-reviewer`, `code-reviewer`) and documentation agents (`document-agent`, `experiment-doc-agent`) reference these rules and add agent-specific scope (which phase, which severity, which subset of D1–D7 applies). When refining detection procedures, edit this section — not the agent files.
