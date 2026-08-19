---
name: sync-kimi
description: "Regenerate Kimi Code's user profile (~/.kimi-code/AGENTS.md, agents/, lib symlink) from the Claude framework in ~/.claude by running scripts/sync-kimi.sh. Invoke when the user types /sync-kimi or asks to update / sync Kimi with the framework (обнови кими, синкни кими, подтяни фреймворк в кими). Works the same from Claude Code and from Kimi Code. Never edits framework files — generation only."
argument-hint: "[--check]"
---

# /sync-kimi — pull the framework into Kimi Code

The framework is edited only in `~/.claude`; Kimi reads a generated copy. This skill runs the generator and reports what happened.

1. Run `"$HOME/.claude/scripts/sync-kimi.sh"` — with `--check` if the user passed it (renders into a temp profile, prints the diff against the live one, writes nothing under `~/.kimi-code`; exit 1 on differences, exit 3 if the tooling failed and nothing could be compared), otherwise plain (writes `~/.kimi-code/AGENTS.md`, `~/.kimi-code/agents/*.md`, refreshes the symlink `~/.kimi-code/lib → ~/.claude/lib`). It needs `npx` and network on the first run (it fetches a pinned rulesync); afterwards the package is cached.
2. Report in the user's language: exit code, the script's stdout/stderr verbatim if non-empty, and — on a plain run — one line naming the three targets written. If stderr says it did not sync (no `npx`, timeout, foreign `CLAUDE_CONFIG_DIR`), say that plainly; do not retry with different flags or try to write the files yourself.
3. Do not edit `~/.kimi-code/config.toml`, `~/.claude/*`, or the generated files by hand. If the user wants a rule changed, it is changed in `~/.claude` and then this skill is run again.
