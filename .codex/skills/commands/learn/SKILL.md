---
name: learn
description: Use when the user invokes /learn or asks to save a reusable learned pattern from the session.
---

# learn

This is the Codex adapter for `/Users/zakharnedashkovskiy/.claude/commands/learn.md`.

When this skill is selected:

1. Read `/Users/zakharnedashkovskiy/.claude/commands/learn.md` completely before taking action.
2. Treat the user's text after the command name as `$ARGUMENTS`.
3. Follow the command contract as the source of truth.
4. Treat Claude-specific tool names as intent and use the closest available Codex tools.
5. If the command asks for a capability that is unavailable in Codex, stop and report the missing capability instead of reconstructing a weaker workflow silently.
