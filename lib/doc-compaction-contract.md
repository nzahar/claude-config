# Doc compaction contract

Cross-cutting rules for keeping `document-agent`-owned codemaps (`docs/CODEMAPS/<area>.md`) and `experiment-doc-agent`-owned `REPORT.md` files from growing without bound, and for keeping a single maintenance pass cheap. Sibling of [`state-contract.md`](state-contract.md), which does the same for `STATE.md`.

This file is the **single source of truth** for the size cap value, the compaction procedure, and the pass-cost process discipline. `rules/workflow.md` § Documentation economy D8 is a pointer here; the agent files reference this file rather than restating its thresholds. When refining any threshold or procedure, edit this file — not the agents.

Two distinct problems are addressed, do not conflate them:

1. **Pass cost.** A dense codemap (lines of 500+ chars) is ~250k tokens for one full read; re-reading it many times and editing it in single-line increments makes one pass cost hundreds of k tokens and tens of minutes. This is fixed by the **process discipline** below — it applies on every pass, regardless of file size.
2. **Artifact size.** Duplicate sections and essay-length table cells inflate the file, which both multiplies pass cost and hurts readability. This is fixed by the **size-triggered compaction** below.

---

## Owner and trigger

The size check is owned by the structural phase of the doc agent: `document-agent` Phase 1 (codemaps), `experiment-doc-agent` Phase 1 (REPORT.md). It runs **unconditionally** at the start of the phase, after the target doc is read and **before** any freshness-hash / no-drift short-circuit, and **outside** any change-volume gate. It fires on the doc's own current size, independent of whether code (or a notebook) changed — so an already-bloated file is compacted on the next pass that touches it, even a one-line one. The check emits a WARNING (no mutation) when the structural portion lands in the `[soft, hard)` band; at or above the hard cap it forces compaction in that pass.

## Budget

Measured over the **structural portion only** = total file lines minus the protected no-touch block. The protected block is **never** counted and **never** compacted — a legitimately large meaning layer must not trigger or suffer compaction. Mechanical boundary:

- **codemap:** protected = the lines between `<!-- MEANING LAYER -->` and `<!-- /MEANING LAYER -->` (inclusive). Structural = every other line.
- **REPORT.md:** protected = the lines under `## Result` (and `## Metrics`, if present) up to the next `## ` heading — these carry verbatim-from-notebook numbers. Structural = every other line.

| Artifact | Soft (WARNING) | Hard (force compaction) |
|---|---|---|
| codemap (`docs/CODEMAPS/*.md`) | 250 structural lines | 400 structural lines |
| `REPORT.md` | 250 structural lines | 400 structural lines |

These are **provisional framework defaults** (per-project override was rejected — one global value). Calibration is _deferred to implementation: on the first real run against a project's docs, confirm the hard cap trips the most-bloated file with margin while the next-largest size-clean file does not; re-tune here if not. Also confirm a token-dense-but-few-lines cell (e.g. a single 3000-char Files cell on one logical line) is actually surfaced by the incremental path (per-section rewrite + soft WARNING + `code-reviewer` D7 tripwire) — the line cap counts lines, not chars, so such a cell can sit under the cap unflagged. If these persist across passes, add a per-cell char-density WARNING distinct from the line cap._

**Fail-safe / bootstrap for un-delimited legacy docs.** If the protected block is not yet delimited (a legacy codemap with no `<!-- MEANING LAYER -->` markers, or a REPORT.md without a clear `## Result`), the size check keys on **total** file lines instead of structural: when total lines exceed the hard cap, run a one-time **delimit-first** pass — identify and wrap the meaning layer (or mark the results section) — then compact normally on the same pass. This breaks the otherwise-circular case where "treat all prose as protected" would zero out the structural count so the file would never compact. Within the delimit step, when in doubt whether a line is meaning or structure, classify it as meaning (never delete).

## Compaction procedure (when the hard cap is exceeded)

Run cheapest-first; the procedure is **loss-proof** — it only deletes content that is provably reconstructable, and relocates everything else verbatim.

1. **Delete only provably-regenerable content; do not blind-delete the rest.** The one section the blind size pass deletes outright is the literal sorted-path-list — its paths are regenerated from the tree by the hash command below, so losing it loses nothing. The duplicate `Module exports` table is **not** deleted by the size pass: it can name symbols a Files cell omits (e.g. value-type dataclasses), so removing it without losing them needs the authoritative source, not a within-doc table-vs-table guess. Folding it into the Files table (the single canonical symbol home) is therefore a **source-aware reconciliation** done by the normal Phase 1 pass — where every symbol comes from the code itself, so nothing documented is dropped — not by this blind size step. `REPORT.md` has no regenerable section — for it, size pressure resolves via cell trimming only.
2. **Trim over-budget cells incrementally — never en masse.** A structural table cell over the ≤200-char budget (D7) is trimmed to a terse role + key exports. Its surplus is split by content type: genuine cross-cutting *why* / gotcha / invariant prose is **moved verbatim** (cut-and-pasted, never paraphrased; after the move, assert the text reappears in the destination) into the destination layer — codemap → meaning layer; REPORT.md → `## Caveats / open questions` (a non-protected section), **never** the protected `## Result` / `## Metrics`. Prose that merely **restates what the code/exports already say is cut**, not relocated (Phase 1: structural cells describe *what*, the meaning layer says *why* — duplicating the exports back as prose is not content to preserve). **Do this per cell as its section is genuinely rewritten — do NOT bulk-relocate every over-budget cell in one size-triggered pass.** Relocating dozens of cells verbatim at once fragments the meaning layer into table-cell dumps and is the move-bloat antipattern; in practice the step-1 deletions usually clear the line cap on their own, after which the remaining over-budget cells are surfaced by the soft-band WARNING and the `code-reviewer` D7 tripwire for incremental attention — not forced in bulk here.
3. **Never touch the protected block.** The meaning layer / results blocks are never deleted or reworded. If the protected block alone approaches the cap, the prescribed escape is to **split** the doc into sub-area files, not to trim it.

**Move-not-edit invariant** (inherited from `state-contract.md`): relocating content is not editing it — the body is preserved verbatim; only its location changes.

**Idempotent re-fire** (like the `state-contract.md` trim — *not* a separate hysteresis band): after compaction the structural portion is below the cap by construction, so the trigger does not re-fire until new code grows it back over the cap. A file hovering at the cap therefore cannot trigger a heavy pass on every PR. The first compaction of a legacy bloated file is a one-time debt paydown.

**Commit shape.** A size-triggered compaction is left as a named, isolated change so a human can commit it on its own: `docs(codemap): compact <area> [size-triggered]` (or `docs(report): …`), with a summary line listing what was dropped and confirming the protected block was preserved. Rollback = the git diff. No backup file, no archive, no approval gate.

## Structure hash (codemaps)

Do **not** store a literal sorted file-path list in the codemap. Keep only the `**Structure Hash:**` header line, computed transiently each pass from the live tree with a pinned, cross-platform command:

`git ls-files <area-paths> | LC_ALL=C sort | git hash-object --stdin`

(`git hash-object` is used rather than `md5`/`md5sum` because the latter differ by platform — `md5` on macOS, `md5sum` on Linux/CI — and would falsely trip the tripwire across machines; `git` is a hard dependency here and its blob hash is deterministic everywhere.) `<area-paths>` = the directory(ies) the codemap covers — the same path set the Files table enumerates. Annotate it with the file count as a cheap add/remove tripwire: `**Structure Hash:** <hash> (<N> files)`. The path list is reconstructable from this command and is already implied by the Files table — keeping a second copy in the file is pure duplication.

## Pass-cost process discipline (applies on every pass, any size)

These are agent-behavior rules with no separate detection procedure (read-once relies on the agent following prose; batch-edit and scope are observable in the pass tool-call trace):

- **read-once.** Read the target doc once and each in-scope source once; hold them in working context. Do not re-read a file "to find the edit site."
- **batch-edit.** Rewrite an affected section in one Edit, not 3–5 single-line edits. (This is the every-pass write discipline. Compaction reuses the same mechanical section-rewrite but is a distinct, size-triggered operation — a routine batch-edit does **not** trigger compaction.)
- **scope-strict.** In a narrow invocation, reconcile only the lines for in-scope files. Do not re-verify the rest of a large doc against the tree.
