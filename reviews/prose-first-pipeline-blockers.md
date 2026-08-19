# Every blocker this plan has drawn — four review rounds, two cycles

The prose-first plan has been through two full `plan-reviewer` cycles (cap 2 each) and
exhausted both with blockers open. This file is the complete record: what was raised,
what closed it, and — the part that matters most — which blockers were *created by the
previous round's fix*. A rewrite that only fixes the latest three findings will draw a
fifth round of the same kind.

Verdicts in order: **6 blockers → 2 → 3 → 3.** Not converging.

---

## Cycle 1, round 1 — 6 blockers (old draft)

1. **The prose call's boundary contract was never stated.** Four typed sites assume a
   dict; `StageRecorder.record` does `dict(raw_output)` (`deps.py:61-67`). A `str`
   return raises *after* the call is billed, leaving no `stage_runs` row — the
   double-buy `boundary.py:251-254` exists to prevent. → closed by D13, `{"markdown": str}`.
2. **ADR-0007's replay-then-rebuy mechanism dropped.** Moving analysis durability to
   `stage_runs.raw_output` lost the `REPLAYS_BEFORE_REBUY` counter; `replay_output`
   (`composition.py:114-131`) has none, so an unparseable answer replays forever with no
   exit but hand-editing the DB. → closed by keeping the counter on `transcripts.analysis`.
3. **The "stage keys are coupled three ways" invariant (`pipeline.md:76`) broken silently.**
   Three config/ledger names under one `_stages()` key. → closed by declaring the split.
4. **The heading check had no rule for the profile's optional block.** `next_opportunities`
   is in `block_order` but in `optional_blocks`; strict list equality bills a repair call
   on every proposal that legitimately omits it. → closed by mirroring `_check_profile:98-106`.
5. **The PDF export gate had no successor.** `render_html(validate=True)` raises on any
   finding and is strictly stronger than the accept gate. §Disposition assigned fates to
   checks as *finding producers* and never mentioned the raise-path. → closed by a row.
6. **Step 6 depended on step 9** — rendering from markdown before the renderer existed.
   → closed by reordering.

## Cycle 1, round 2 — 2 blockers, both born from round 1's own fixes

7. **Delivery days lost mechanism and check in one move.** The §Disposition rework of
   finding 5 split `_check_provenance` into two rows and left `:130-137` with none, while
   D4 had no delivery island — so `inject_server_values`' unconditional overwrite
   (`composition.py:305-309`) vanished with nothing replacing it. A fabricated delivery
   window would ship in an accepted PDF. → closed by `{{delivery_window}}`.
8. **"Impossible by construction" was over-claimed.** The totality of `_check_commercials`
   came from the *structured contract*, not from server rendering: with typed fields the
   model could not write money anywhere else. Prose has no such fields.
   `composition.py:352` *suppresses* the discount rather than rendering it, so
   `unapproved_discount` became undetectable, not impossible. → closed by §Numbers in prose
   and D14's scan.

## Cycle 2, round 1 — 3 blockers (draft rewritten from scratch)

9. **D2's prose brief could not produce the artifact D2 claimed to preserve.** "brief
   (prose)" against `composition.py:89-91` (raises unless `lead_brief` and `task_spec` are
   Mappings), `:411-413` (`task_spec["id"]`/`["version_id"]`), `:480`
   (`lead_brief["policy_contradictions"]` — nested, and the draft listed it as a top-level
   field). Four rounds passed before anyone checked. → closed by removing prose from
   analysis entirely: three grammar calls.
10. **The only text-editing path was deleted while D10 called markdown "the editable
    source of truth".** `PATCH /blocks` removed, no replacement; combined with a PDF gate
    that never consults dismissals, any unrepairable finding meant an accepted proposal
    whose `/pdf` 409s forever. → closed by D15.
11. **`forbidden_block` lost its mechanism.** It is unreachable today only because
    `BlockKind` (`proposal/models.py:54-64`) has no member for any forbidden id — the typed
    contract *is* the enforcement, and prose removes it. → closed by making D5's heading
    check a closed list.

## Cycle 2, round 2 — 3 blockers, two of them born from round 1's fixes

12. **A measurement error in the main session's own fix.** §Goal claimed brief+task_spec
    at 4,351 B; that is `lead_brief` **alone**. Together they are **6,891 B**, so the
    margin to the 10,895 refusal is 1.58×, not 2.5×, and step 10's "≤ 5 KB" assertion
    would have failed on the first run against the contract D2 mandates.
13. **The PDF gate's severity semantics contradicted themselves.** D15 said "raises on any
    surviving **error**"; §Disposition said the same call is re-pointed "raising on any
    surviving **finding**". Today's code is the latter (`validation.py:317-318`, no
    severity filter), so the WARNING introduced in the previous fix would block the PDF
    forever — re-opening blocker 10 exactly.
14. **"Routed to repair" was unreachable at WARNING severity.** `repair.py:43` builds its
    payload from `_is_blocking` (`:88-89`) = `severity == "error" and not dismissed`, and
    `:44-45` returns early on an empty list. The WARNING severity chosen to fix blocker 10
    made D14 advisory-only: the fabricated discount would be counted and never rewritten.
    → closed by dropping the severity trick: `prose_numeric_literal` is an ordinary ERROR,
    and D15's edit route is what keeps an unrepairable finding from being terminal.

---

## The pattern, stated plainly

**Five of the fourteen blockers were created by the fix to a previous blocker** (7, 8, 13,
14, and arguably 12). The mechanism is always the same shape: a check or a mechanism is
removed or re-pointed, and the *reason it was total* is not the reason the plan assumed.

Three specific traps this plan keeps falling into:

- **Totality came from the type system, not from the server.** `_check_commercials`,
  `forbidden_block`, `_check_provenance`'s delivery days, `unapproved_snippet` — each was
  airtight because a typed field or a `BlockKind` enum made the alternative unrepresentable.
  Prose makes every one of them representable again. Ask of *every* retired check: was it
  total because the server computed the value, or because the model had nowhere to put a
  different one?
- **A finding's severity is load-bearing in three places at once** — the repair payload
  filter (`_is_blocking`), the accept gate (`has_blocking_findings`, which honours
  dismissals), and the export gate (`validate_proposal`, which does not). Changing severity
  to fix one breaks another.
- **Mechanism and check are a pair.** `inject_server_values` writes a field and
  `_check_provenance` verifies it; retiring one without the other leaves either an
  unchecked value or an uncheckable one.

## What is currently in the plan and believed correct

The current draft is `docs/plans/prose-first-pipeline.md` at commit `c88274a`, 228 LOC,
with blockers 12–14 fixed but **self-verified only** — no reviewer has seen those fixes.

Measurements reproduced twice, by the main session and independently by the reviewer, on
one basis (adapted schema, `$ref` expanded, `$defs` retained):

| contract | bytes |
|---|---|
| analysis (today, refused) | 10,895 |
| `proposal-content` (refused) | 140,980 |
| grounding review (passed) | 449 |
| brief+task_spec | 6,891 |
| `lead_brief` alone | 4,351 |
| `task_spec` alone | 3,169 |
| units | 2,307 |
| roles+contradictions | 2,055 |

Every `file:line` in the draft was verified against the tree by the reviewer at both
`70a6256` and the draft before it; none was stale.
