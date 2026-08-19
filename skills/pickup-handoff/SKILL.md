---
name: pickup-handoff
description: "Read the session handoff written by /handoff for the current project into this session and continue from its Next steps. Invoke when the user types /pickup-handoff, or says to pick up / continue from the handoff (подхвати handoff, продолжи с handoff). Read-only: never moves, deletes or rewrites the handoff file — run it twice and nothing changes. NOT /handoff (that one writes)."
---

# /pickup-handoff — read the handoff for this project

The previous session left a handoff file outside the project. Your job is to read it, tell the user what you found, and continue from its § Next steps. Nothing injects it automatically and nothing consumes it on read — reading is side-effect-free.

## 1. Resolve the path

One file per project. Ask the script — it prints the full path and nothing else:

```
"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks/handoff-path.sh" "<session's working directory>"
```

Pass the session's working directory — the one named in your environment context — as a literal absolute path, not `$(pwd)`: the Bash tool's cwd persists across calls and may have drifted into another repository. `/handoff` resolved the path the same way; a different input here means looking where nothing was written.

If the script prints nothing or fails, stop and tell the user the handoff path cannot be resolved. Do not guess a path.

## 2. Read it — or say plainly there is nothing

Read the file at the printed path with the Read tool.

If it does not exist, say so in one line: **there is no handoff for this project**, name the path you checked, and stop. Do not look in `_archive/`, do not offer to write one, do not search other projects' handoffs — the user asked a yes/no question and got the answer.

## 3. Report and continue

In the user's language, in a few lines:

- the file path and its modification time (`ls -l`) — the user decides whether it is stale;
- § Goal in one sentence and the first item of § Next steps;
- anything in § Verification status marked UNVERIFIED, and the uncommitted-work note if § Git snapshot showed a dirty tree — re-check `git status` now and say whether it still matches.

Treat § Verification status as claims, not facts — re-run the commands listed there before relying on them. Then continue from § Next steps unless the user redirects.

## Never

- Move, archive, delete or edit the handoff file. History is `/handoff`'s job, at write time. If the file is stale, that is the user's call to make on the mtime you reported.
- Fall back to `_archive/` — an archived handoff is one the user already replaced.
