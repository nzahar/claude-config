# STATE.md contract

Specification for the format of `docs/STATE.md` and its split-mode counterparts (`docs/RESEARCH-STATE.md`, `docs/STATE-ARCHIVE.md`, `docs/RESEARCH-STATE-ARCHIVE.md`).

Two agents author STATE files and reference this contract for shared rules:
- `document-agent` Phase 3 — engineering trajectory in `docs/STATE.md`
- `experiment-doc-agent` Phase 4 — research trajectory in `docs/STATE.md` or `docs/RESEARCH-STATE.md` (in `split` mode)

Each agent's own definition keeps the agent-specific parts: ownership matrix entry, list of Current fields, sources for each field, examples. Everything below applies to both.

---

## File structure

A STATE file is a single living document with two sections: `## Current` (overwritten on each update) and `## History` (append-only, newest entries on top).

Standard header:

```
# STATE — <project-name>

_Last updated: YYYY-MM-DD HH:MM_
```

Sections that follow:
- `## Current` — present-state snapshot. The field list is agent-specific
- `### Notes` (subsection of Current) — free-form short observations
- `## History` — compressed entries, newest on top

## Compressed History shape

Each History entry is **at most ~10 lines**. It is *not* a verbatim copy of the previous Current — it is a compressed record produced by the Demote step of the agent's workflow.

A History entry contains:
- Header line: `### <existing Last-updated timestamp> — <one-line summary of what changed in that snapshot>`
- 2–3 bullets naming material decisions / blockers cleared / status transitions of that snapshot. **Each bullet must carry an inline reference**: `(see ADR-NNNN)`, `(PR #N)`, `(plan docs/plans/<slug>.md §X)`, `experiments/<domain>/<slug>/REPORT.md`, `findings/<slug>.md`, `BACKLOG #N`, `<file>:<symbol>`. Bullets without inline references are dropped — load-bearing content lives in ADRs / plans / REPORT.md / codemaps / git, the inline ref is how a future reader finds it

**Dropped during demotion** (do not carry into History): full Notes block, Read-order TOCs, paraphrase of plan-file content, per-experiment narrative recaps, Recently-shipped DDL pastes, full narrative explanations. The original detail remains reachable via the inline references above.

Prepend the compressed entry to `## History` (newest on top). Do not edit existing History entries — they were produced by past compression and are immutable.

**Pre-existing History entries** may include a `**Last shipped:** <PR ...>` line — that line reflects an earlier version of this contract. Per `## History is sacred`, leave such entries intact: do not rewrite, do not flag as drift, do not strip the line. New entries written under this contract omit the line.

### Same-day guard

If the existing Current's `_Last updated:_` date matches today's date, **overwrite Current in place without demoting**. History is for trajectory across days, not micro-snapshots.

## Invariant under merge

**Every field in Current must remain valid after a squash-merge of the current feature branch.** Test each value: "would this still be true after `git merge`?" If not, decompose or drop.

Forbidden because they decay at merge:
- `Active branch:`, `In progress: <X> (uncommitted)`, `🛠️ Working tree (<branch>): …`, `Awaiting commit + push`, `Pre-merge triad in progress`
- Commit hashes (`abc1234`)

Allowed (stable URLs / immutable artifacts):
- PR numbers (`#42`)
- Plan file paths (`docs/plans/<branch-slug>.md`)
- ADR references (`ADR-NNNN`)
- REPORT.md paths (`experiments/<domain>/<slug>/REPORT.md`)

Trajectory fields describe *what's been done and what's planned* (or *what's being researched*), independent of git deployment, and remain valid through merge.

"What's being built right now" lives in `docs/plans/<branch-slug>.md` (the plan file), not in STATE.md.

## Hex-string constraint covers all of Current

**No hex strings of the form `[0-9a-f]{7,}` in any value in Current**, including free-text Notes and any agent-specific fields.

Exception: a hex inside a quoted command or URL that is itself a stable artifact reference (e.g. `pip install git+...@<sha>`) is allowed, but such content usually belongs in a codemap, ADR, REPORT.md, or findings/ — when in doubt, move the bullet out of STATE.md.

## Next up formatting

**Mechanical git actions (`commit`, `push`, `open PR`, `merge`) are never Next up items** — they happen, they don't appear in STATE.md.

**Branch names (`feature/...`, `fix/...`, `release/...`) are forbidden anywhere in Next up** — branches get deleted on squash-merge.

Reference the plan file path (`docs/plans/<branch-slug>.md`) if one exists; otherwise describe the work itself in one line. If the working tree has uncommitted work, describe what happens **after** commit+push+merge (e.g. "by user: review coauthor draft", "complete plan X", "revise paper draft"), not the mechanics. Use `by user: …` prefix when the next action requires a user command (review, decision, manual step).

## References, not copies, in Notes

If a Notes bullet duplicates content available in an ADR, plan file, codemap, REPORT.md, findings/, or git history — replace with `(see ADR-NNNN §X)` / `(see plan §Y)` / `<file>:<symbol>` / `experiments/<domain>/<slug>/REPORT.md` instead of pasting content inline.

Test for each bullet: "if I delete this, is anything lost that isn't recoverable from ADR / plan / codemap / git / REPORT.md?" If no — drop.

Exceptions worth keeping inline are snapshot operational facts not recorded elsewhere (live system state, observed counts, environment-specific gotchas).

## No Read-order block

Do not write a "Read order for cold-start" list in Current or in any History entry. If a project genuinely needs a stable onboarding pointer list, it lives in `docs/ONBOARDING.md`, not inside STATE.md.

## Hard cap on size

After the file has settled into its final shape this run (whether the Demote step compressed history or the same-day guard overwrote Current in place), count lines:

- If `## History` exceeds **400 lines** OR the managed STATE file exceeds **600 lines** — move the oldest History entries to the archive file until back under both caps. Moving an entry is **not editing** — the entry body is preserved verbatim; only its location changes
- Insert moved entries **immediately after the archive's title line**, before any existing first archived entry (newest archived first; the title stays at line 1)
- If the archive does not exist, create it with a single-line title `# STATE archive — <project>` (or `# RESEARCH STATE archive — <project>` for the research-side archive in split mode) above the entries
- Existing `STATE-HISTORY-<year>.md` files from a prior age-based rule coexist — new writes go to the new archive target
- Cap trigger is **size**, not age — young projects with fast rhythm hit it before "6 months old" would

**Archive target by `state_owner`:**

| `state_owner` | Main file | Archive file |
|---|---|---|
| `document-agent` (or absent on engineering project) | `docs/STATE.md` | `docs/STATE-ARCHIVE.md` |
| `experiment-doc-agent` (or absent on research-only project) | `docs/STATE.md` | `docs/STATE-ARCHIVE.md` |
| `split` — engineering half | `docs/STATE.md` | `docs/STATE-ARCHIVE.md` |
| `split` — research half | `docs/RESEARCH-STATE.md` | `docs/RESEARCH-STATE-ARCHIVE.md` |

## Hard limit on Current size

Current ≤ **30 lines total**, including the Notes subsection. If it doesn't fit, the overflow belongs in an ADR, codemap, REPORT.md, findings/, or fresh `docs/ONBOARDING.md` (if read-order) — not in STATE.md.

## Pre-merge gates are never project state

`code-reviewer` pass, `document-agent` / `experiment-doc-agent` pass, `test-writer` pass — none of these belong in Blocked, Next up, Open cross-experiment questions, or Notes. They are workflow between branch and main and disappear at merge. If the user is waiting on review feedback that needs their decision, attribute to `by user: …` in Next up instead.

## No severity vocabulary in STATE.md

STATE.md is descriptive, not graded. Drift comments use `<!-- DRIFT: ... -->` markers, not severity.

Severity vocabularies are **agent-local** and do not transfer across agents. They live in each agent's own output, not in STATE.md:

- `CRITICAL` / `HIGH` / `MEDIUM` / `LOW` / `NEEDS VERIFICATION` — `code-reviewer`, in review reports
- `blocker` / `warning` — `plan-reviewer`, in plan-review reports
- `TODO` / `WARNING` — `experiment-doc-agent` Phases 1–3, in REPORT.md and the domain README
- `debugger` has no severity vocabulary by design — findings are root-cause statements, not graded issues

This block is the canonical cross-agent reference; each agent file states its own vocabulary and points back here.

## Anti-duplication

STATE.md is about *now*, not about *what the code does* or *why it was decided*. Three concrete duplication patterns to actively avoid:

- **ADR / plan / REPORT.md rationale pasted inline.** If a Notes bullet explains *why* something is the way it is, that belongs in an ADR — reference it with `(see ADR-NNNN §X)`, do not paraphrase. For research, full result narratives belong in REPORT.md, not STATE.md
- **Recently-shipped DDL, code, figure, or table blocks.** If a bullet contains `CREATE TABLE`, full SQL, a multi-line code fence, or a figure caption, it belongs in the codemap / REPORT.md / `git show <commit>` — reference the commit / PR / REPORT.md, do not paste
- **Recently-shipped commit narrative inline.** If a Notes bullet paraphrases "shipped X" or "just merged Y", drop it — `git log main --merges -1 --pretty=%s` is the source. Notes captures snapshot facts not in git (live system state, environment-specific gotchas), not git-history paraphrase

## History is sacred

Never edit a compressed History entry once it has been written by a past pass. Corrections go in the next Current update.

## Cadence

The STATE update phase (`document-agent` Phase 3, `experiment-doc-agent` Phase 4) runs only:
- As the final phase of a full pass
- On explicit `--state-only` invocation

Skip the STATE update phase entirely if the session was purely exploratory and produced no decisions, no blockers, and no plan changes — nothing has happened that needs to be picked up.

Routine drift updates or routine merges with no plan-state shift do NOT auto-trigger STATE update.

## Ask the user at most once at the end

If you cannot derive Current fields from code / git / REPORT.md, batch the question for the end of the phase — do not block mid-update.
