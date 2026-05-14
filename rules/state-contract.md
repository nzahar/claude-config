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
- One `**Last shipped:** <PR # + title only>` line — no value description suffix
- 2–3 bullets naming material decisions / blockers / status changes of that snapshot. **Each bullet must carry an inline reference**: `(see ADR-NNNN)`, `(PR #N)`, `(commit abc1234)`, `(plan docs/plans/<slug>.md §X)`, `experiments/<domain>/<slug>/REPORT.md`, `findings/<slug>.md`, `BACKLOG #N`, `<file>:<symbol>`. Bullets without inline references are dropped — load-bearing content lives in ADRs / plans / REPORT.md / codemaps / git, the inline ref is how a future reader finds it

**Dropped during demotion** (do not carry into History): full Notes block, Read-order TOCs, paraphrase of plan-file content, per-experiment narrative recaps, Recently-shipped DDL pastes, full narrative explanations. The original detail remains reachable via the inline references above.

Prepend the compressed entry to `## History` (newest on top). Do not edit existing History entries — they were produced by past compression and are immutable.

### Same-day guard

If the existing Current's `_Last updated:_` date matches today's date (multiple invocations the same day — morning sync + afternoon sync), **overwrite Current in place without demoting**. History is for trajectory across days, not micro-snapshots. Demoting the same day twice creates History entries identical except for timestamp and pollutes the record.

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

## Last shipped formatting

Field value = title + PR number of the most recent merged PR. **Strip any commit hash from the title before quoting** — `git log --oneline` and raw `git log` output include the hash; drop it. The field value must contain **no hex strings of the form `[0-9a-f]{7,}`**.

Source of merge subjects: `git log main --merges -3 --pretty=format:"%s"`, or `gh pr list --state merged --limit 3` if available. "none" if no merges yet.

Add one short line of value description (what changed for users / for the system / for research) — see the calling agent for domain-appropriate framing.

**If there is an open (unmerged) PR on the current branch, do not describe it in Last shipped.** Last shipped names only merged PRs; an open PR's existence belongs in its plan file, not here.

## Hex-string constraint covers all of Current

The `[0-9a-f]{7,}` no-hex rule from Last shipped applies to **every value in Current, including free-text Notes and any agent-specific fields**. Commit hashes anywhere in Current decay the same way.

Exception: a hex inside a quoted command or URL that is itself a stable artifact reference (e.g. `pip install git+...@<sha>`) is allowed, but such content usually belongs in a codemap, ADR, REPORT.md, or findings/ — when in doubt, move the bullet out of STATE.md.

## Next up formatting

**Mechanical git actions (`commit`, `push`, `open PR`, `merge`) are never Next up items** — they happen, they don't appear in STATE.md.

**Branch names (`feature/...`, `fix/...`, `release/...`) are forbidden anywhere in Next up** — branches get deleted on squash-merge.

Reference the plan file path (`docs/plans/<branch-slug>.md`) if one exists; otherwise describe the work itself in one line. If the working tree has uncommitted work, describe what happens **after** commit+push+merge (e.g. "by user: review coauthor draft", "complete plan X", "revise paper draft"), not the mechanics. Use `by user: …` prefix when the next action requires a user command (review, decision, manual step).

## References, not copies, in Notes

If a Notes bullet duplicates content available in an ADR, plan file, codemap, REPORT.md, findings/, or git history — replace with `(see ADR-NNNN §X)` / `(see plan §Y)` / `<file>:<symbol>` / `experiments/<domain>/<slug>/REPORT.md` instead of pasting content inline.

Test for each bullet: "if I delete this, is anything lost that isn't recoverable from ADR / plan / codemap / git / REPORT.md?" If no — drop.

Exceptions worth keeping inline are snapshot operational facts that aren't recorded elsewhere (live system state, observed counts, environment-specific gotchas).

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

Split-mode separation prevents engineering and research entries from being interleaved under one title.

## Hard limit on Current size

Current ≤ **30 lines total**, including the Notes subsection. If it doesn't fit, the overflow belongs in an ADR, codemap, REPORT.md, findings/, or fresh `docs/ONBOARDING.md` (if read-order) — not in STATE.md.

Treat "doesn't fit" as a signal that Notes is paraphrasing something that should live elsewhere — promote it, don't shrink the font.

## Pre-merge gates are never project state

`code-reviewer` pass, `document-agent` / `experiment-doc-agent` pass, `test-writer` pass — none of these belong in Blocked, Next up, Open cross-experiment questions, or Notes. They are workflow between branch and main and disappear at merge. If the user is waiting on review feedback that needs their decision, attribute to `by user: …` in Next up instead.

## No severity vocabulary in STATE.md

STATE.md is descriptive, not graded. Drift comments use `<!-- DRIFT: ... -->` markers, not severity.

Agent-local severity vocabularies belong in their own outputs, not in STATE.md:
- `TODO` / `WARNING` from `experiment-doc-agent`'s Phases 1–3 belong in REPORT.md and the domain README
- `CRITICAL` / `HIGH` / `MEDIUM` / `LOW` from `code-reviewer` belong in review reports
- `blocker` / `warning` from `plan-reviewer` belong in plan-review reports

Each agent's severity model is local to its domain.

## Anti-duplication

STATE.md is about *now*, not about *what the code does* or *why it was decided*. Three concrete duplication patterns to actively avoid:

- **ADR / plan / REPORT.md rationale pasted inline.** If a Notes bullet explains *why* something is the way it is, that belongs in an ADR — reference it with `(see ADR-NNNN §X)`, do not paraphrase. For research, full result narratives belong in REPORT.md, not STATE.md
- **Recently-shipped DDL, code, figure, or table blocks.** If a bullet contains `CREATE TABLE`, full SQL, a multi-line code fence, or a figure caption, it belongs in the codemap / REPORT.md / `git show <commit>` — reference the commit / PR / REPORT.md, do not paste
- **Read-order TOC.** A list of "1. read this file, 2. read that ADR, 3. read this plan" inside STATE is duplication of pointers that already exist in ADR / README, plan headers, codemap indexes, and REPORT.md sections. Drop it — if a stable onboarding sequence is genuinely needed, that's `docs/ONBOARDING.md`

## History is sacred

Never edit a compressed History entry once it has been written by a past pass — even if you now think it captured the wrong things, it was an accurate record of what was emphasized at the time. Corrections go in the next Current update.

## Cadence

The STATE update phase (`document-agent` Phase 3, `experiment-doc-agent` Phase 4) runs only:
- As the final phase of a full pass
- On explicit `--state-only` invocation

Routine drift updates or routine merges with no plan-state shift do NOT auto-trigger STATE update. STATE.md churn destroys history value.

## Ask the user at most once at the end

If you cannot derive Current fields from code / git / REPORT.md, batch the question for the end of the phase — do not block mid-update.
