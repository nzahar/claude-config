Commit changes, open a PR, and merge it immediately.

**Pre-merge gates check.** For each of the three gates, answer: (a) does it apply to the branch diff? (b) if it applies — did it return APPROVED for the current state (not a stale snapshot)?

Applicability criteria:

- **`code-reviewer`** — there is code, configuration, or framework artifacts (`rules/`, `agents/`, `CLAUDE.md`, `commands/`, `skills/` except `learned/`, `docs/ADR/`, `lib/`) — including edits to existing ADRs and `lib/` documents, not only new ones. **Not** applicable: micro doc edits (≲10 lines of prose — heuristic; edits that change contract or semantics require review regardless of size), typos, rephrasings.
- **`test-writer`** — there are changes to code with testable logic. **Not** applicable: pure documentation, configuration without behavioural effects, renames.
- **`document-agent` / `experiment-doc-agent`** — the repo has `docs/CODEMAPS/`, `docs/STATE.md`, or `experiments/` with REPORT.md. **Not** applicable: repos without these artifacts (e.g., the framework itself in `~/.claude/`).

**What counts as a stale snapshot.** A gate's APPROVED covers the diff state it was invoked on. Any commit afterwards that adds behaviour, logic, or contract the gate never evaluated makes the snapshot stale — **this rule dominates the exemption below.** Exemption (`code-reviewer` only): applying its **own** findings at **medium severity or below** does **not** restale the snapshot *when each fix is mechanical and confined to the code the finding named* — a rename, dead-code removal, comment, or the exact narrow guard the reviewer specified. A medium finding whose fix introduces new logic (e.g. "add input validation here", "guard this empty case") is **not** exempt — that fix is code the gate never saw, so it restales. Fixes addressing a high/critical finding always restale. Cross-gate effects: `test-writer` adding tests for already-reviewed code does **not** restale `code-reviewer`; `document-agent` / `experiment-doc-agent` edits to docs, `STATE.md`, or codemaps never restale the code gate.

Decision:

- All applicable gates returned APPROVED → silently move to step 1.
- An applicable gate did not pass, or passed on a stale snapshot → stop, name the missed gate, propose to run it, wait for an explicit "continue".
- Neither an applicability nor a non-applicability criterion clearly fits a particular gate → ask the user about that gate, do not generalise. (Narrow case — not the default "I am generally unsure" path.)

**Mode detection.** Determine the mode once:

```bash
git remote get-url origin | grep -qE '127\.0\.0\.1|localhost|local_proxy' && echo cloud || echo local
```

Steps below are common to both modes; mode-specific steps are marked **Local:** / **Cloud:**.

**Cloud-quirks for all MCP calls below.** Before every `mcp__github__*` call — `ToolSearch` with the specified `query`. Parameter names, method/action, enum values — strictly from the real schema, **do not guess** from prose names. `owner`/`repo` — the last two segments of `git remote get-url origin` without `.git`; if a proxy-format URL does not parse — ask the user.

**Steps:**

1. Show `git status`. If there are no changes — stop.

2. Check for secrets among the changed files (`.env`, `credentials`, `*.pem`, private keys). If any — stop and warn.

3. Prepare the branch.
   - **Local:** on `main`/`master` create a new one (`feature/<slug>` or `fix/<slug>`); on a feature/fix branch — commit to the current one.
   - **Cloud:** do not create a new one — commit to the current `claude/<slug>-<hash>` (the proxy allows push only to that one; any other → 403).

4. Stage files **explicitly by name** (not `git add .` / `-A`). If more than ten files — ask which ones to commit.

5. Commit with a conventional message in English (`feat:` / `fix:` / `refactor:` / `docs:` / `chore:`), then push.
   - **Local:** `git push -u origin <branch>`.
   - **Cloud:** `git push -u origin HEAD`.

6. Create the PR. Body: **Summary** (bullets — what), **Motivation** (why), **Changed files** (table). Remember the created PR number as `<N>`.
   - **Local:** `gh pr create --title ... --body ...` via HEREDOC; `<N>` — the last segment of the output URL. If no `gh` — tell me.
   - **Cloud:** `mcp__github__create_pull_request` (query: `select:mcp__github__create_pull_request`). Parameters: `head` = `git rev-parse --abbrev-ref HEAD`, `base` = `main`; `<N>` — the `number` field in the response.

7. Check the PR status.
   - **Local:** `gh pr view <N> --json state,mergeable,statusCheckRollup`.
   - **Cloud:** `mcp__github__pull_request_read` (query: `select:mcp__github__pull_request_read`). Need `state`, `mergeable`, the state of checks. If you cannot get it in one call — make two.
   - Not MERGEABLE (conflicts) → stop, show the reason. Checks failed → warn and ask whether to continue.

8. Merge as squash + delete branch.
   - **Local:** `gh pr merge <N> --squash --delete-branch`. **Do not add `--repo`** — explicit `--repo` switches gh to API-only mode and skips local-branch cleanup (leftovers for step 10).
   - **Cloud:** `mcp__github__merge_pull_request` (query: `select:mcp__github__merge_pull_request`). Parameters: `mergeMethod: "squash"`, `deleteBranch: true`, `pullNumber: <N>`.

9. Switch to main and pull.
   - **Local:** `git checkout main && git pull origin main && git fetch --prune`.
   - **Cloud:** `git fetch origin main && (git checkout main 2>/dev/null || git switch -c main origin/main) && git pull origin main` (without `fetch --prune`: the remote branch was already deleted by the MCP merge; local `git push --delete` is forbidden by the proxy).

10. Delete the local feature branch.
    - **Local:** `git branch -d <branch> 2>/dev/null` (silently, no error if absent).
    - **Cloud:** skip — runtime will create a new session branch.

**Recovery from a partial failure.**
- Steps 1–5 failed → fix the cause, restart `/ship` (PR not yet created).
- Steps 6–10 failed → PR already on remote. **Do not restart `/ship`** (repeat commit/PR-create will lead to 422 / confusion). Recover: `gh pr view <N>` (or MCP equivalent) → resolve the cause → continue from step 7 or invoke `/merge-pr <N>`.

---

_Canonical single-step versions — `commands/commit-push.md` and `commands/merge-pr.md`. When changing them (a new safety check, MCP schema change, proxy rule update), verify that `/ship` is still correct._
