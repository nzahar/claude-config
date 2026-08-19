# plan-reviewer round 2 — prose-first-pipeline.md (verdict: BLOCKED)

Reviewed at commit `d0dc8d5`, branch `feature/prose-first-pipeline`, mode engineering.
This was the **second and final** round of that review cycle; the cap is exhausted, so
the prescribed exit is `/clear` + cold-start rewrite of the draft, never implementation.

**Both blockers below were already fixed in `993a7cf`, after this report was written.**
The fixes are recorded here so the cold-start rewrite can check them rather than
rediscover them. The rewrite must also bring the file back under the 200-LOC soft
trigger — it stands at 227.

## What the round confirmed as genuinely closed

All six round-1 blockers, each verified against code rather than wording:

- **D13 / prose call contract.** `deps.py:61-67` confirms `dict(raw_output)` at `:67`;
  a `str` return raises there after billing. The four typed sites are real and
  correctly located (`boundary.py:33-44`, `:320`, `:321/:328/:360`, `:399`). The one
  remaining schema-assuming site, `_decode(text, assets.output_schema, usage)` at
  `:379`, is unreachable for prose once the `:360` arm exists.
- **D11 counter placement terminates.** `_replayable` (`analysis.py:89-94`) gates on
  `parse_failures > REPLAYS_BEFORE_REBUY`; `_with_parse_failure` (`:97-102`) increments
  in the `except` around the whole assembly. For a three-call stage: 0 → replay,
  1 → replay, 2 → all three re-bought. The ungated hazard is real —
  `composition.replay_output` (`:114-131`) has no counter.
- **Stage-key coupling set is complete.** `ANALYSIS_STAGE` resolves to exactly
  `analysis.py:58`, `:59`, the loader sites already enumerated
  (`assets.py:104/107/137/144`) and `validate_phase0.py:52`; `context.record(
  context.stage, …)` at `:64` is the third site. `bootstrap.py:37` spreads
  `**analysis_assets.stages` generically and needs no edit; `_stages()`
  (`__init__.py:37`) keeps `"analysis"`.
- **D5 heading check** mirrors `_check_profile:98-106` accurately, and the
  `next_opportunities` rationale is factually right (`profile.v1.json:17` and `:33`).
- **PDF gate row.** `validate_proposal` recomputes findings from `content` and never
  consults stored dismissals, so "a dismissed error still blocks the export" is true.
- **Step reordering** is correct — rendering (step 6) precedes the readers (step 7).

Also confirmed: no DDL needed (`stage_runs` carries no CHECK on `stage`,
`tables.py:118-129`; `content`/`analysis`/`findings` are JSON); `markdown-it-py` is
routed to both manifests that exist (`pyproject.toml`, `environment.lock.yml`; there
is no `environment.yml`); ADR positioning is accurate against ADR-0004/0007/0009 Scopes;
`docs/ADR/README.md` does lack the ADR-0009 row. Documentation economy passes on all
seven rules.

## Blocker 1 — delivery days lose their server mechanism and their check together

`inject_server_values` (`composition.py:305-309`) today overwrites
`delivery_days_min`/`delivery_days_max` unconditionally from `projection.delivery_days`,
and `_check_provenance` (`validation.py:130-137`) rejects any other provenance. The
draft split `_check_provenance` into two §Disposition rows (`:114-124` estimate/policy,
`:125-129` client context) and left `:130-137` with no row, while D4's placeholder set
had no delivery island and §Principle listed only money, disclaimers and the cover.
`composition_payload:574` still handed `delivery_days` to the model. Net effect: the
model writes a delivery commitment in `implementation_plan` prose, nothing overwrites
it, nothing checks it — a fabricated delivery window ships in an accepted PDF.

It also breaks two recorded invariants the draft never acknowledged: `pipeline.md:82`
("`inject_server_values` is unconditional… so a model that invents a number cannot land
one on the document") and `domain.md` §Gotchas ("delivery days must be
`estimator_output` or `human_override`").

**Fixed in `993a7cf` by:** a fifth placeholder `{{delivery_window}}` (D4); §Disposition
rows for `_check_provenance:130-137`, the cover date (`composition.py:303`) and
`_with_pricing_assumption` (`:326-328`); `composition_payload:574` stops passing
`delivery_days`; §Goal acknowledges both codemap invariants as carried, not dropped.

## Blocker 2 — "impossible by construction" over-claimed

Today the model can only emit commercial values into typed fields that the server
overwrites — the *structured contract* is what makes `_check_commercials` and
`unapproved_discount` total, not server rendering as such. Prose has no such
constraint, and none of the draft's post-processing steps inspected numbers.

Sharpest instance: `composition.py:352` forces `first_month_discount_percent = None` —
the server **suppresses** the introductory offer rather than rendering it. Step 12
nevertheless listed `unapproved_discount` among ten codes "expected to vanish by
construction" and demanded the breakdown show they vanished "because their inputs are
server-rendered". For that code the input is not server-rendered and cannot be: the
model can write "первый месяц −20%" in narrative and no layer sees it. Same shape for
a total quoted in prose that contradicts `{{estimate_table}}`. Step 12 would report a
clean run for a failure class that became undetectable rather than impossible.

**Fixed in `993a7cf` by:** a new §Numbers in prose and decision D14 — a scan over the
assembled markdown outside the islands raising `prose_numeric_literal` on any currency
amount, percentage, or hours figure, routed to repair; §Principle gains an explicit
statement of its own limit; step 12's ten codes are split into nine
impossible-by-construction and `unapproved_discount` + prose-quoted totals as
caught-not-impossible, with a zero count admissible only if step 10 proves the scan live.

## Warnings from round 2 (all folded into `993a7cf`)

- Island format unspecified while two decisions constrain it — HTML islands would trip
  `_MARKUP_PATTERN` (`validation.py:35-38`) and be escaped by D9's renderer. → D4 now
  pins islands as markdown.
- D11 counter granularity unpinned. → increments once per stage run, replay decision
  per call.
- `provider_assets.py:115` is a second unconditional `output_contract` read, and
  `OpenAIStructuredProvider` reads `assets.output_schema` unguarded at `boundary.py:142`
  and `:161` (dead under `PROVIDERS=anthropic`, and the repo has no mypy/pyright config).
  → both named in step 2.
- Steps 5 and 9 named no files. → the deterministic layer lands in
  `proposal/markdown.py`; step 9 names `review.py:36` and `repair.py:55`.
- The tree does not boot between steps 2 and 3 (config bumps ahead of the assets they
  hash-pin). → the `config_version` bumps moved into step 3.

## Line-reference nits, corrected in `993a7cf`

`estimate.py:59` → `:61` (the `work_units` read); `analysis/assets.py:195-215` →
`:195-216` (`output_schema = _load_json(schema_path)`); `api/proposals.py:136` → `:133`
(the gated call, not the `except`); `ProjectPage.tsx:189` → `:190` (the mount, not the
guard).

Everything else resolved exactly: `assets.md:62`, `pipeline.md:76`,
`composition.py:114-131`, `:589`, `review.py:36`/`:38`, `repair.py:55`/`:68`,
`html.py:76-84`, `validation.py:114-124`/`:125-129`, `validate_phase0.py:52`/`:53-57`/
`:275-287`/`:317-323`, `provider_assets.py:15`/`:27`/`:94`/`:101`, `api.ts:139`,
`types.ts:124`, `blocks.ts` ← `BlockEditor.tsx:2` (sole consumer), `smoke.test.tsx:145`,
`EvidenceError`/`AmbiguousQuoteError` in `analysis/evidence.py:10`/`:25`.

## Left for the doc agent, not this plan

`docs/CODEMAPS/assets.md:13`, `:15`, `:61`, `:71` still say `analysis-v4` /
`proposal-workflow.v3` against `analysis-v6` / `proposal-workflow.v4` in code —
pre-existing staleness on the base branch, and the same lines take the v7/v5 bump.
