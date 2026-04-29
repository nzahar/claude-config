## Task Workflow — Spec → Plan → Review → Code

For any non-trivial task, follow this sequence strictly:

1. **Agree on the spec** — clarify requirements, constraints, edge cases with the user before planning
2. **Write a visible implementation plan** — markdown file at `docs/plans/<branch-slug>.md` (where `<branch-slug>` is the branch name without the `feature/` or `fix/` prefix). The user can read and edit it; commit it to the repo so the user owns it. Before drafting: identify which modules/areas the work touches, then read `docs/CODEMAPS/<area>.md` for each (focus on meaning-layer blocks) and any ADR in `docs/ADR/` whose Scope covers the affected paths. The plan must reference relevant ADRs explicitly ("respects ADR-NNNN", "supersedes ADR-MMMM"), acknowledge invariants from meaning-layer blocks, and — if the work conflicts with an existing ADR — propose a superseding ADR rather than ignoring the existing one
3. **Get explicit user approval** — wait for the user to confirm the plan before going further
4. **Run `plan-reviewer` on the plan** — six-dimension review (requirement coverage, task completeness, dependency correctness, schema/infra drift, ADR/CODEMAPS compliance, verification plan). The agent returns blockers and warnings; show them to the user. The user (with main session help if needed) decides what to fix. Do not loop with the agent — one report, then decide. Skip this step only for small tasks (see exception below)
5. **Implement step by step** — one logical chunk at a time, not a big-bang generation. When implementing larger features, decompose into independent vertical slices and dispatch parallel subagents

For small tasks where a full plan would be overkill: state the approach in one sentence and confirm before coding. Steps 2 and 4 do not apply — there is no plan file to review.

Never jump straight to code.
