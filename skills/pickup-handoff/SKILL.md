---
name: pickup-handoff
description: "Read the session handoff written by /handoff for the current project into this session and continue from its Next steps. Invoke when the user types /pickup-handoff, or says to pick up / continue from the handoff (подхвати handoff, продолжи с handoff). Consumes what it reads: the handoff is moved into docs/handoffs/archive/ (uncommitted). NOT /handoff (that one writes)."
---

# /pickup-handoff — read the handoff for this project

The previous session left a handoff file in the project, under `docs/handoffs/`. Your job is to read it, tell the user what you found, archive it, and continue from its § Next steps. Nothing injects it automatically.

## 1. Resolve the path

Handoffs live at `<repo>/docs/handoffs/<YYYY-MM-DD-HHMM>.md`. Resolve the repo root by anchoring git at the session's working directory:

```
git -C "<session's working directory>" rev-parse --show-toplevel
```

Pass the session's working directory — the one named in your environment context — as a literal absolute path, not `$(pwd)`: the Bash tool's cwd persists across calls and may have drifted into another repository. `/handoff` resolved the root with this same `-C`-anchored command; a different anchor here means looking where nothing was written.

If the command fails — not a git repository — stop and tell the user the handoff path cannot be resolved. Do not guess a path.

Then list the pending handoffs, newest last, without descending into the archive:

```
ls -1 "<repo>/docs/handoffs"/*.md 2>/dev/null
```

The names are `YYYY-MM-DD-HHMM`, so newest-by-name is newest-by-time — take the last one. Any others are pending handoffs the user never picked up; they are archived in § 3 unread.

## 2. Read it — or say plainly there is nothing

Read the newest file with the Read tool.

If `docs/handoffs/` holds no `.md` file, say so in one line: **there is no handoff for this project**, name the directory you checked, and stop. Do not look in `archive/`, do not offer to write one, do not search other projects' handoffs — the user asked a yes/no question and got the answer.

## 3. Archive what you read

Move the file you just read into the archive, and every other pending handoff with it — unread; they are superseded by the one you took:

```
mkdir -p "<repo>/docs/handoffs/archive"
git -C "<repo>" mv "docs/handoffs/<file>" "docs/handoffs/archive/<file>" || mv -n "<repo>/docs/handoffs/<file>" "<repo>/docs/handoffs/archive/<file>"
```

`mkdir -p` first and the plain-`mv` fallback are both load-bearing: `git mv` aborts on a missing destination directory and on an untracked source — an untracked handoff is the normal case in a repo that ignores `docs/`. The fallback is `mv -n` so an already-archived file is never overwritten; on a name collision the pending file simply stays put for a later pickup.

**Do not commit the move.** It rides along with this session's next regular commit.

## 4. Report and continue

In the user's language, in a few lines:

- the handoff's name — its timestamp says how stale it is — and where it sits now: `docs/handoffs/archive/`, uncommitted, along with any other pending handoff you archived unread (name only what actually moved — an `mv -n` collision leaves a file pending);
- § Goal in one sentence and the first item of § Next steps;
- anything in § Verification status marked UNVERIFIED, and the uncommitted-work note if § Git snapshot showed a dirty tree — re-check `git status` now and say whether it still matches.

Treat § Verification status as claims, not facts — re-run the commands listed there before relying on them. Then continue from § Next steps unless the user redirects.

## Never

- Read `archive/` on your own initiative — only when the user explicitly asks for an older handoff. What is in there has already been picked up.
- Delete or rewrite a handoff. Archiving is the only move you make, and git keeps the rest.
