Run the following steps:

**Mode detection.** At the very start, determine the mode by the `origin` URL:

```bash
git remote get-url origin | grep -qE '127\.0\.0\.1|localhost|local_proxy' && echo cloud || echo local
```

If the result is `cloud` — we work via the GitHub MCP in the single permitted session branch. If `local` — `gh` CLI and push to any branch. Steps common to both modes appear without a prefix; mode-specific steps are marked **Local:** / **Cloud:**.

**Atomicity.** This command does only commit and push. Review, tests, documentation updates — separate steps before or after. Full policy — `CLAUDE.md` §"Atomicity of commands".

1. Show `git status` — understand what changed and what is untracked.
2. Verify there are no secrets among the changed files (.env, credentials, private keys, *.pem). If there are — stop and warn.
3. Prepare the branch.
   - **Local:** if the current branch is `main` or `master` — create a new branch with a meaningful name (format: `feature/short-description` or `fix/short-description`). If already on a feature/fix branch — commit to the current one, do not create a new one.
   - **Cloud:** **do not create a new branch** — the current branch (`claude/<slug>-<hash>`) is the single permitted session branch; commit to it.
4. Stage files **explicitly by name** (not `git add .` and not `git add -A`). If more than ten files changed — ask which ones to commit before staging.
5. Make the commit with a meaningful message in English (conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`).
6. Push the branch.
   - **Local:** `git push -u origin <branch>`.
   - **Cloud:** `git push -u origin HEAD` (push is allowed only to the current session branch; any other gets 403 from the proxy).
7. Create a Pull Request with the description:
   - **Summary** — what changed (bullets)
   - **Motivation** — why
   - **Changed files** — table of files with a brief description

   The body template is shared between modes; only the transport differs.

   - **Local:** `gh pr create` with `--title` and `--body` (HEREDOC). If `gh` is not installed — tell me.
   - **Cloud:** before the call, fetch the MCP tool schema via `ToolSearch` with `query: "select:mcp__github__create_pull_request"` (field names in the schema are the source of truth — do not guess). Then call `mcp__github__create_pull_request` with parameters:
     - `head` — name of the current branch (`git rev-parse --abbrev-ref HEAD`)
     - `base` — `main`
     - `title` — same as in local
     - `body` — same Summary/Motivation/Changed files template
     - `owner`, `repo` — extract from `git remote get-url origin` (the last two path segments without `.git`). The cloud URL is a proxy (`http://...@127.0.0.1:<port>/<owner>/<repo>`), but owner/repo are still the last two segments. If for any reason they do not parse — ask me instead of guessing.
