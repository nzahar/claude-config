---
name: statusbar-theme
description: Switch the status-bar color theme (graphite / twilight / linen)
---

# statusbar-theme

This is the Codex adapter for `/Users/zakharnedashkovskiy/.claude/commands/statusbar-theme.md`.

When this skill is selected:

1. Read `/Users/zakharnedashkovskiy/.claude/commands/statusbar-theme.md` completely before taking action.
2. Treat the user's text after the command name as `$ARGUMENTS`.
3. Follow the command contract as the source of truth.
4. Treat Claude-specific tool names as intent and use the closest available Codex tools.
5. If the command asks for a capability that is unavailable in Codex, stop and report the missing capability instead of reconstructing a weaker workflow silently.
