Find the PR with number $ARGUMENTS and merge it.

**Mode detection.** At the start determine the mode by the `origin` URL:

```bash
git remote get-url origin | grep -qE '127\.0\.0\.1|localhost|local_proxy' && echo cloud || echo local
```

If `cloud` — merge and checks go via GitHub MCP; local `git push --delete` is forbidden by the proxy. If `local` — `gh` CLI works directly. Steps common to both modes appear without a prefix; mode-specific steps are marked **Local:** / **Cloud:**. Extract `owner` and `repo` for MCP calls from `git remote get-url origin` (the last two path segments without `.git`); if the URL is a proxy and does not parse, ask me.

1. Check PR status.
   - **Local:** `gh pr view $ARGUMENTS --json state,mergeable,statusCheckRollup`.
   - **Cloud:** before the first call, fetch the schema via `ToolSearch` with `query: "select:mcp__github__pull_request_read"` and read the actual method/action names from the schema. Do not guess values from prose names — if the schema's enum does not match expectation, use what is in the schema. You need both the overall PR status (state, mergeable) and the state of checks. If you cannot get it in one call — make two with different method values.
   - In both modes: if the PR is not MERGEABLE (conflicts) — stop and show the reason; if checks failed — warn and ask whether to continue.
2. Merge as squash + delete branch.
   - **Local:** `gh pr merge $ARGUMENTS --squash --delete-branch`.
   - **Cloud:** before the call — `ToolSearch` with `query: "select:mcp__github__merge_pull_request"`, read the schema. Then call with `mergeMethod: "squash"`, `deleteBranch: true`, `pullNumber: $ARGUMENTS`, `owner`, `repo` (parameter names per the schema, if different from those listed).
3. Switch to main.
   - **Local:** `git checkout main`.
   - **Cloud:** `git fetch origin main && (git checkout main 2>/dev/null || git switch -c main origin/main)`. A local `main` branch may not exist in a fresh session — hence the `switch -c` fallback.
4. Pull updates: `git pull origin main` (read-only through the proxy, allowed in cloud too).
5. Clean remote refs.
   - **Local:** `git fetch --prune`.
   - **Cloud:** skip — the remote branch deletion was handled by the MCP merge with `deleteBranch: true`; local `git push --delete` is forbidden by the proxy.
6. Delete the local feature branch if any remains.
   - **Local:** `git branch -d <branch> 2>/dev/null` (silently, no error if absent).
   - **Cloud:** skip — runtime recreates the session with a new `claude/<slug>-<hash>`; the local feature branch is not needed.
