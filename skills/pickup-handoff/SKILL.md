---
name: pickup-handoff
description: Read the session handoff written by /handoff for the current project into this session and continue from its Next steps. Invoke when the user types /pickup-handoff, or says to pick up / continue from the handoff (подхвати handoff, продолжи с handoff). Consumes what it reads — a tracked handoff file is deleted (uncommitted), git keeps it; one git refuses to remove is left in place. NOT /handoff (that one writes).
---

# /pickup-handoff — read the handoff for this project

The previous session left a handoff file in the project, under `docs/handoffs/`. Your job is to read it, tell the user what you found, delete it, and continue from its § Next steps. Nothing injects it automatically.

## 1. Resolve the path

Handoffs live at `<repo>/docs/handoffs/<YYYY-MM-DD-HHMM>.md`. Resolve the repo root by anchoring git at the session's working directory:

```
git -C "<session's working directory>" rev-parse --show-toplevel
```

Pass the session's working directory — the one named in your environment context — as a literal absolute path, not `$(pwd)`: the Bash tool's cwd persists across calls and may have drifted into another repository. `/handoff` resolved the root with this same `-C`-anchored command; a different anchor here means looking where nothing was written.

If the command fails — not a git repository — stop and tell the user the handoff path cannot be resolved. Do not guess a path.

Then list the handoffs, newest last:

```
ls -1 "<repo>/docs/handoffs"/*.md 2>/dev/null
```

The names are `YYYY-MM-DD-HHMM`, so newest-by-name is newest-by-time — take the last one. Any others are earlier handoffs the user never picked up; leave them where they are.

## 2. Read it — or say plainly there is nothing

Read the newest file with the Read tool.

If `docs/handoffs/` holds no `.md` file, say so in one line: **there is no handoff for this project**, name the directory you checked, and stop. Do not offer to write one, do not search other projects' handoffs — the user asked a yes/no question and got the answer.

## 3. Delete what you read — if git has a copy

Only the file you read — earlier handoffs stay for a later pickup:

```
git -C "<repo>" rm -q "docs/handoffs/<file>"
```

If git refuses — the file is untracked (a repo that ignores `docs/`) or locally modified — leave it where it is and report git's message in § 4; the user deletes it by hand. Never `rm` a handoff yourself. In such a repo the newest file may be one an earlier session already consumed — say so when its § Git snapshot is older than the live log. **Do not commit the deletion** — it rides along with this session's next regular commit.

## 4. Report and continue

In the user's language, in a few lines:

- the handoff's name — its timestamp says how stale it is — and that it is deleted (uncommitted), or left in place with git's reason;
- § Goal in one sentence and the first item of § Next steps;
- anything in § Verification status marked UNVERIFIED, and the uncommitted-work note if § Git snapshot showed a dirty tree — re-check `git status` now and say whether it still matches.

Treat § Verification status as claims, not facts — re-run the commands listed there before relying on them. Then continue from § Next steps unless the user redirects.

## Never

- Read an older handoff on your own initiative — only when the user explicitly asks; `git log -- docs/handoffs` finds deleted tracked ones.
- Rewrite a handoff. Deleting the one you read is the only change you make.
