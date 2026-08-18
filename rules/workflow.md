## Task Workflow — Spec → Plan → Review → Code

Every task starts with track selection at intake. The numbered sequence below is the **full track**; tasks that pass the intake tests run on the **light track** instead.

**Track selection (intake).** Two tests:

- **Diff enumerability** — before starting, write out the files to be changed and one line per file on what changes. If the list cannot be enumerated confidently, the task is not small → full track.
- **Blast radius** — a §4.5-trigger operation is expected, an irreversible write, a file in any ADR's Scope, or a public contract/schema change → full track regardless of diff size.

Both tests pass → light track. When in doubt → light track: the cost of a false "small" is bounded by the tripwires below.

**Light track.** Start with a declaration: one sentence of approach + the enumerated file list. Work starts immediately after publishing it — no waiting for confirmation; the user sees the declaration and can interrupt. The file list is the baseline for tripwire (b).

Tripwires — any one fires → mandatory escalation to the full track:

- (a) the first fix attempt failed;
- (b) a file outside the declared list is needed;
- (c) a fork surfaced that would have to be recorded in a plan;
- (d) a file in some ADR's Scope was touched, missed at intake.

The ratchet is one-way: light → full at any moment; full → light mid-task — never. Escalation keeps the working tree: write a plan for the remaining work, recording decisions already made, then continue on the full track from step 2.

End of a light-track task: commit and push. The pre-merge triad is **not** auto-dispatched — a light-track task routinely lands mid-session with no merge in sight, and the triad is a branch-level pre-merge gate, not a task-level one. It fires on the same trigger as on the full track: the one defined in CLAUDE.md §Pre-merge triad.

Unchanged on the light track: §4.5 pre-execution review, Verification Before Claims, PR/merge gates, conventional commits, one branch per feature. Tripwires and §4.5 are orthogonal axes: a §4.5 trigger fires the one-shot operation review, not a track switch. Exploratory notebook work fails the enumerability test ("try and see" is not enumerable) and follows the existing rules — no separate research variant.

**Full track:**

1. **Agree on the spec** — clarify requirements, constraints, edge cases with the user before planning
2. **Write a visible implementation plan** — markdown file at `docs/plans/<branch-slug>.md` (where `<branch-slug>` is the branch name without the `feature/` or `fix/` prefix). The user can read and edit it; commit it to the repo so the user owns it. Before drafting: identify which modules/areas the work touches, then read `docs/CODEMAPS/<area>.md` for each (focus on meaning-layer blocks) and any ADR in `docs/ADR/` whose Scope covers the affected paths. The plan must reference relevant ADRs explicitly ("respects ADR-NNNN", "supersedes ADR-MMMM"), acknowledge invariants from meaning-layer blocks, and — if the work conflicts with an existing ADR — propose a superseding ADR rather than ignoring the existing one. Three authoring rules bind the plan text: **No claim without evidence** — a statement about code or data carries `file:line`, or an executed read-only probe whose output is recorded in the plan. **No risk without evidence** — a gate, step or fallback for a risk earns its place only when a named instance exists (measurement, incident, `file:line`, codemap block); a hypothetical risk gets one line or is cut (SSOT: D9 in §Documentation economy). **Zero growth on revision** — a revised draft stays ≤ previous draft + 10 % LOC; revisions replace text, they do not append (this is the SSOT for zero growth; §Discipline rule 6 points here). Probes are project-local reads and greps by default; a probe that matches a §4.5 trigger goes through §4.5 first
3. **Get explicit user approval** — wait for the user to confirm the plan before going further
4. **Run `plan-reviewer` on the plan** — seven-dimension review (requirement coverage, task completeness, dependency correctness, schema/infra drift, ADR/CODEMAPS compliance, verification plan, documentation economy). The agent returns blockers and warnings; show them to the user. Skip this step only on the light track (no plan file exists)
   - **Classes and gate.** Every blocker carries a class line `Surfaces at: <moment> → class R|I`; the class test itself is SSOT in `agents/plan-reviewer.md` (I = a named irreversible cost lands before anything catches it; R = a mechanical signal or the pre-merge review reaches it first). A blocker without a class line is invalid: the main session applies the class test itself and downgrades to a warning only when it cannot name an irreversible cost. **Only I blockers gate implementation.** R blockers the main session fixes into the plan text per the fix hint (or declines, stating why), no re-review required. Fix open I blockers and run another round within the cap that applies
   - **Round ≥ 2 invocation contract (SSOT).** The prompt names the previous report (path or inline) and lists each R blocker with its fix or its declined status; the agent's round ≥ 2 pass is scoped to that report, not a full pass
   - **Cap and exits.** Hard cap: 2 reviewer invocations on the same draft for non-framework plans, outside the extension rule. At the cap: no I open → fix remaining R inline, implementation authorized (remaining warnings are accepted or fixed at the user's call); I open and the I count strictly decreased vs the previous round → one extension round, repeatable while I keeps strictly decreasing; I open and not decreased → scrap-and-rewrite, which per "Counting" means `/clear` + cold-start — never implementation. **The I count** is every I blocker in the latest report, newly discovered ones included; a full-pass round (round 1, or a round ≥ 2 run without dispositions) resets the comparison baseline — the round counter itself never resets outside "Counting". A strictly decreasing I series is the converging case that Loop hygiene below does not interrupt
5. **Implement step by step** — one logical chunk at a time, not a big-bang generation. With an approved plan, delegating delegable slices to background subagents is the default — criteria and contract in **Slice delegation** below

**Slice delegation (step 5 default).** With an approved plan on file, decompose the work into vertical slices; a slice is dispatched to a background subagent by default when it passes all three criteria:

- **Fully specified by the plan** — the agent reads `docs/plans/<branch-slug>.md` itself; if executing the slice would require decisions the plan does not fix, it is not delegable
- **Disjoint write targets** — the slice's file set does not overlap other concurrent slices; if overlap is unavoidable, dispatch with the Agent tool's `isolation: worktree` and resolve the seams in the main session
- **No interactive iteration expected** — anything "try and see" stays in the main session

**Exclusions — and they win over the criteria:** exploratory coding, small edits (~≤2 files with context already loaded), and hard debugging are never delegated, even when fully plan-specified. Small work is faster by hand; hard debugging needs the strongest model with full context (or the `debugger` agent per its own contract).

**Model:** implementation agents run on Opus by default (`general-purpose` agent type, `model: opus` — no dedicated contract file). Escalate a slice to Fable only on explicit user request or when the slice is architecture-core; justify the escalation in one line at dispatch.

**Dispatch prompt must contain:** the plan file path; the exact file list the agent may write (write scope); the required report format (changed files; commands run, with output); a prohibition on §4.5 trigger-list operations. The prohibition is a backstop layered on the no-interactive-iteration criterion — a slice that inherently needs a §4.5 operation self-excludes from delegation; it is not an expected mid-flight path.

**Verification:** the agent runs its slice-level tests and includes the output in its report. The agent does not commit — it leaves changes for the main session to commit (worktree slices included). The full suite, cross-slice seams, and any completion claim stay with the main session — an agent's report is second-hand evidence under CLAUDE.md §Verification Before Claims.

**Exception to "no loop" — framework / governance changes** (applies to step 4 plan-reviewer **and** any reviewer cycle whose artifact is a framework document, including `code-reviewer` on a rules/agents diff). When the change under review is itself an edit to a framework / governance document, iterate review→revise with the reviewer until clean — for `plan-reviewer` cycles: no I blockers and no warnings (R blockers fixed inline); for `code-reviewer` cycles: no CRITICAL/HIGH introduced by the diff, and every new MEDIUM either fixed or explicitly declined with a reason — pre-existing tech debt, LOW, nits and NEEDS VERIFICATION do not block (classes exist only in plan review).

**Framework hard cap: 3 reviewer invocations on the same draft.** After round 3, choose one explicitly — ship with remaining warnings (nits, taste-level), scrap-and-cold-start (`/clear`, rewrite from plan + last reviewer report — counts as a new cycle, not a continuation), or decompose (split one artifact into multiple — typically rule + ADR, or two narrower rules). For `plan-reviewer` cycles the step-4 cap exits refine this: no I open → fix remaining R inline, then ship-with-warnings or decompose; I open and strictly decreasing → one extension round; I open and not decreasing → scrap-and-cold-start. Outside the extension rule, never invoke reviewer for round 4 on the same draft.

**Counting.** "Round" counts only formal reviewer invocations (`plan-reviewer`, `code-reviewer`) on the same draft. Both reviewers share the same counter when applied to the same artifact. Conversation with the user does not count toward the cap. "Same draft" = the artifact carried forward across reviewer rounds: edits made in response to the previous round's findings, including structural revisions, stay the same draft and do not reset the counter. Only `/clear` + cold-start rewrite from the plan file plus last reviewer report produces a new draft with a fresh counter — that is the intended escape valve for "scrap and cold-start", not a loophole to reset the counter on the same exhausted draft.

**Smoke beats review on data work.** This applies to the step 4 / framework `plan-reviewer` loops above — not to §4.5 pre-execution review (which is one-shot per code path). For changes that touch data per the §4.5 trigger list (principle and examples there — wide reading on purpose, includes operations that match the principle but no enumerated trigger): when the cap is exhausted with remaining warnings (and no I blockers open), running smoke against real data is an additional exit option alongside the listed alternatives in each cap branch (non-framework: step 4 "Cap and exits"; framework cap=3: ship-with-warnings, scrap-and-cold-start, decompose).

**Operational test for "framework-level"** (a change qualifies if a flawed version reliably propagates into future sessions whenever its trigger fires — base-prompt load, agent invocation, slash-command, etc.):

- **Always in scope** (full content loaded every time the trigger fires, trigger fires frequently): `rules/`, `CLAUDE.md`, `agents/`, ADRs — base-prompt auto-load every session for `rules/` and `CLAUDE.md`; full prompt load on every agent invocation for `agents/`
- **In scope on contract changes only** (invoke-on-demand, trigger fires rarely, many edits are prose tweaks): `commands/`, `skills/*` (excluding `learned/`) — iterate when changing **what** the artifact takes/returns or **when** it triggers (description, arguments, output shape, trigger phrasing). Skip iteration for prose tightening, added examples, rationale rewrites
- **Excluded**: `skills/learned/*` (knowledge base, not governance), regular feature work, bugfixes, `workflow.md` §4.5 (operation-level pre-execution review — that gate stays one-shot per code path)

**Loop hygiene.** If iteration extends beyond ~3 cycles (except a strictly decreasing I series per step 4), stops converging (each new cycle introduces new warnings from previous fixes — a regression loop, not progress), or context becomes heavy, suggest `/clear` + cold-start from the plan file plus the latest reviewer report. Consistent with design-discipline rule #5 (`/compact` ban during design work).

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

**Escape valve.** The user may explicitly override ("skip review, trivial") only for "long-running" and "external read of free/internal resources" categories. **Not applicable to** irreversible writes (DDL/DML on shared/prod, mass deletes, artifact uploads) or metered/paid budgets (rate-limited paid API, GPU-hour billing). **For light-track tasks**, override applies only to the "long-running" category — external reads still require review.

**Mode selection.** Invoke `code-reviewer mode: research` if the code is an experiment notebook or training/eval pipeline (file uses `model.fit`, `optimizer.step`, `Trainer`, `--epochs`, or similar), regardless of project-level `default_agent_mode`. Otherwise invoke in default (engineering) mode.

One report, then decide — §4.5 is one-shot per code path, not a 2-round mini-loop.

Never start code before the intake declaration (light track) or an approved plan that has cleared plan review (full track).

## Discipline within long design sessions

Long design sessions (multi-iteration plan-review, ADR drafting, multi-question spec discussions) accumulate conflicting drafts in conversation context. The rules below counter this with mostly objective triggers (file edits, explicit user phrases, session events) plus a few interpretive ones that still require reading context. When uncertain, bias toward the action. Each rule fires independently — there is no "design mode" switch.

| # | Trigger | Action |
|---|---|---|
| 1. **Sub-plan = source of truth** | User confirms a design decision (`ok`, `согласен`, `accepted`, equivalent) on something that belongs in the plan, **and a plan file exists for the current branch** | **Immediately** Edit `docs/plans/<branch-slug>.md` to record the decision, before continuing the conversation. Do not "remember and continue" — written plan is durable, conversation is transient. On the light track this rule does not fire — a decision that would need recording in a plan is tripwire (c) and escalates to the full track |
| 2. **Re-grounding at session start** | Start of any session in a git repo | Extends `CLAUDE.md` §"Project State Awareness" — in addition to `docs/STATE.md`, also read the current branch's plan file at `docs/plans/<branch-slug>.md` if it exists. The base rule's trivial-edits exception and the scope-known ADR/CODEMAPS rule continue to apply |
| 3. **Discard alternatives in plan** | Editing a plan file, writing a decision section | Plan: **only the current decision**, zero rejected alternatives. ADR: brief mention of rejected approach (risk + revisit trigger), not a parallel implementation. If a rejected option is load-bearing enough to need long-form description — that goes into a future superseding ADR at the moment of revisit, not as preemptive bloat in the current ADR |
| 4. **No branching across two substantive design questions** | User asks Q2 of design-substantive level (requires reasoning + plan record) while Q1 of the same level is unanswered | Close Q1 first by recording in plan, then move to Q2. **Short factual / clarification / yes-no questions batch as usual** — this rule is about parallel design-state, not about being terse |
| 5. **`/compact` ban during design work** | User invokes `/compact` (or asks "compact this conversation") during a session that has done plan / ADR / spec edits or active design discussion | Stop and suggest `/clear` + cold-start from the plan file. **Never** `/compact` — compaction silently loses decision nuance. Trigger on the explicit user invocation, not on self-detected "context bloat" |
| 6. **Plan size soft trigger (non-framework)** | Non-framework plan in `plans/` grows past ~200 LOC during revision | Explicit refactor pass before next reviewer invocation. Soft signal, not hard cap — defensive bloat is the typical cause; legitimate multi-system plans may exceed 200 LOC. Per-revision growth is bounded separately by the step-2 zero-growth rule (≤ +10 % LOC per revision) |

**Session boundaries at phase transitions.** When the plan file marks a phase as done and the next phase is structurally different (design → implementation, implementation → synthesis, design → ADR write-up), suggest the user start a fresh session.

These rules apply project-agnostically to any full-track task following the spec → plan → review → code workflow above.

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

- **D9. Risk plausibility in plans.** A mitigation in `docs/plans/*.md` — a step, gate or fallback framed as guarding against a risk — earns its place only when the risk has named evidence. Hypothetical risks are one line or cut.
  - _Authoring:_ Do not add a step, gate or fallback for a risk without a named instance — a measurement, an incident, a `file:line`, or a codemap block — in the same bullet, table row or sentence. If the only justification is "could happen", write one line under a risks list or cut it. Mirror of the reviewer rule "a blocker requires a concrete failure mode".
  - _Detection:_ for each step, gate or fallback in `docs/plans/*.md` framed as a mitigation (trigger phrases: "guard against", "in case", "if X fails", "to prevent", "fallback", "defensive"), check for an evidence reference (`file:line`, a number with a source, an incident or report name, a codemap section, or an explicit pointer to an evidence block elsewhere in the same document) in the same bullet, table row or sentence. None → 1 finding per mitigation. Severity: `plan-reviewer` warning, `code-reviewer` MEDIUM. Heuristic — never a blocker.
  - _Scope:_ `docs/plans/*.md` only. Not ADRs, not codemaps, not REPORT.md.

**Application across agents.** Detection procedures above are the single source of truth. Reviewer agents (`plan-reviewer`, `code-reviewer`) and documentation agents (`document-agent`, `experiment-doc-agent`) reference these rules and add agent-specific scope (which phase, which severity, which subset of D1–D9 applies). When refining detection procedures, edit this section — not the agent files.
