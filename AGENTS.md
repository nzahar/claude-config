# Codex Adapter for the Claude Framework

This file is the Codex-facing adapter for the framework in this repository.
Treat the canonical sources as:

- `CLAUDE.md` for the Claude Code adapter.
- `AGENTS.md` for the Codex adapter.
- `rules/`, `agents/`, `skills/`, `commands/`, and `hooks/` for shared framework contracts.

Do not edit generated Codex files in `~/.codex` by hand. Update this repository
and run `scripts/sync-codex.py --install` instead.

## Language & Communication

- Reply in Russian if the user writes in Russian, English if English.
- Code, commits, PRs, documentation artifacts, and code comments are always in English.
- Be brief. Do not repeat what is already visible in a diff.
- Do not add preambles, praise, or recap unless it changes what the user should do.
- For short answers, prefer prose over bullets.

## Code Discipline

- Do not write code comments by default. Add a comment only when removing it would make future maintenance materially harder.
- Use the repository's existing patterns before introducing new abstractions.
- Keep edits scoped to the user's request and the files needed to verify it.

## Project State Awareness

At the start of every session in a project, read `docs/STATE.md` if it exists.
Read only `## Current` unless the user asks for history or prior decisions.

- If `docs/STATE.md` is absent, do nothing.
- If the user contradicts `docs/STATE.md`, trust the user.
- Never edit `docs/STATE.md` from the main session. It is owned by the documentation agent.
- Do not surface `docs/STATE.md` content unprompted.

When working outside the formal workflow, read relevant `docs/CODEMAPS/*.md`
and ADRs under `docs/ADR/` if the work touches recorded architecture or
invariants. Skip this for trivial local fixes.

## Verification Before Claims

Do not claim that tests pass, builds succeed, migrations ran, endpoints work,
dependencies installed, or behavior is fixed without fresh verification in the
current turn. Run the command that proves the claim and summarize its output.

If verification fails, report the failure instead of claiming completion.

## Tool Hygiene

- Use `rg` / `rg --files` for search.
- Do not use `sed`, `cat`, `head`, `tail`, `awk`, `echo`, or `printf` through a shell for file reading, file writing, or user-facing text.
- Use dedicated file editing tools when available. For manual code edits in Codex, prefer `apply_patch`.
- Leave shell commands for process execution, tests, git, dependency tools, and tree search.

## Workflow

Use `/Users/zakharnedashkovskiy/.claude/rules/workflow.md` as the canonical task
workflow. For full-track tasks, follow spec -> plan -> review -> code. For
light-track tasks, publish the one-sentence approach and enumerated file list
before editing.

Framework and governance changes include `rules/`, `CLAUDE.md`, `AGENTS.md`,
`agents/`, ADRs, and contract changes in `commands/` or non-learned `skills/`.
They require reviewer iteration as described in `rules/workflow.md`.

## Subagents

Use Codex custom agents generated from `/Users/zakharnedashkovskiy/.claude/agents/*.md`
when the task matches their role. The Claude contracts remain the source of
truth; the generated Codex agent files only point Codex at those contracts.

Long-running or multi-step subagent work should run in the background. For
branch-level pre-merge checks, run `code-reviewer`, `test-writer`, and the
appropriate documentation agent in parallel when the user explicitly asks for
merge-readiness checks.

## Commands

Use Codex command skills generated from `/Users/zakharnedashkovskiy/.claude/commands/*.md`
when the user invokes a slash-command by name or uses the command's natural
trigger. For example, "зашипай" / "ship it" maps to the generated `ship` skill,
which must read and follow `commands/ship.md`.

## Git & Shipping

- Use conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`.
- Use one branch per feature or fix.
- `git commit`, `git push` to a feature branch, and `docker push` are part of the normal implementation flow and do not need an explicit request.
- Never open a PR or merge to `main` without an explicit user request. This covers `gh pr create`, `gh pr merge`, and their MCP analogs `mcp__github__create_pull_request` and `mcp__github__merge_pull_request`. Do not self-invoke the `ship` or `merge-pr` command skills either — the user invoking one is itself the explicit request.
- Trigger words that authorize the PR/merge phase: «/ship» / «шипай», «/merge-pr <N>», «merge», «мерж(и)», «открой PR» / «open PR», «создай PR» / «create PR».
- Ambiguous instructions ("сделай", "имплементируй", "продолжай", "do", "implement", "continue") authorize commit and push, never PR or merge.

## Stack Preferences

- Python 3.12 with conda environments.
- FastAPI + async lifespan for Python services.
- Go for performance-critical services.
- React + TypeScript for frontend work.
- PostgreSQL with async SQLAlchemy 2.x / asyncpg in Python, pgx in Go.
- Alembic for Python migrations, golang-migrate for Go migrations.
- Docker Compose for local infrastructure.

## Library Documentation

For library, framework, SDK, CLI, cloud-service, API syntax, configuration,
migration, or version-specific debugging questions, prefer current docs through
context7 when available before relying on memory.
