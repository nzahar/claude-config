---
name: handoff
description: "Write a session handoff file so a fresh session can cold-start the current work. Invoke when the user types /handoff [optional focus], or asks to prepare a handoff for a new session (context nearly full, wrapping up with continuation expected). The next session reads it explicitly with /pickup-handoff; nothing injects it automatically. Commits only its own docs/handoffs file and pushes the current branch — it touches no other working-tree change."
argument-hint: "[focus]"
---

# /handoff — session handoff

You are wrapping the current session's state into a file a fresh session can act on with zero conversation history. The handoff is judged by one criterion: **can the next session continue safely using only this file and the repo?** Write it while you still can — a handoff authored at 95% context is authored by a degraded session; do not defer the invocation.

## 1. Parse the invocation

`/handoff [focus]` — **focus** (optional free text) is what the user wants emphasized (a specific bug, a subtask); weave it into Goal / Next steps, do not add sections.

## 2. Resolve the target path

The handoff goes inside the project: `<repo>/docs/handoffs/<YYYY-MM-DD-HHMM>.md`. One file per run — existing handoffs are never overwritten (the sole exception: a rerun in the same minute deliberately replaces that minute's file) and never deleted from here (`/pickup-handoff` deletes what it consumed).

Resolve the repo root by anchoring git at the session's working directory:

```
git -C "<session's working directory>" rev-parse --show-toplevel
```

Pass the session's working directory — the one named in your environment context — as a literal absolute path. Do **not** substitute `$(pwd)`: it evaluates in the Bash tool's cwd, which persists across calls and may have been moved into another repository. `/pickup-handoff` resolves the root with the same `-C`-anchored command from the next session's real cwd; a different anchor here means the next session looks where nothing was written and reports "no handoff".

If the command fails — not a git repository — **stop and tell the user the handoff path cannot be resolved.** Do not guess a path — a guessed path is a file nothing will ever read.

Then create the directory and take the timestamp (local time):

```
mkdir -p "<repo>/docs/handoffs" && date +%Y-%m-%d-%H%M
```

The file lives in the repo on purpose: committed in § 4a, it reaches the other machines and the co-authors who work on this project — a handoff parked on one disk does not.

If `docs/handoffs/` already holds handoffs — a previous session's, not yet picked up, or already consumed in a repo that ignores `docs/` — read the newest first and carry forward still-valid content, especially What did NOT work.

## 3. Collect the git snapshot mechanically

Run and capture verbatim (do not paraphrase, do not summarize):

```
git branch --show-current
git status --porcelain
git log --oneline -5
git diff --name-only
```

This block goes into § Git snapshot as-is.

## 4. Write the handoff

Use the template below. Constraints:

- **English** (documentation), with the reply-language line in the header (e.g. "Reply in Russian").
- **Narrative ≤ ~1000 words** (excluding § Git snapshot and fenced blocks). Budget forward: Next steps and What did NOT work outrank history — git recovers finished work, dead ends are irrecoverable.
- **Absolute paths** for every file mentioned.
- **Error messages verbatim**, never paraphrased.
- **Self-contained**: no "as discussed", no references to the conversation, no unresolved pronouns. Every referent resolves within the file.
- **Pointers, not duplicates**: link ROADMAP.md, codemaps, plan files, ADRs — do not restate their content.
- **Claims carry evidence**: anything asserted as done/passing names the command and its outcome in § Verification status. What you did not verify this session, mark unverified — the next session re-checks before trusting.
- If `git status --porcelain` is non-empty, § Current state must say what the uncommitted changes are — they are invisible to the next session's `git log`. Remind the user (outside the file) that uncommitted work is at risk; the handoff file is the **only** thing you commit (§ 4a), never their work.

## Handoff template

```markdown
# Handoff — <task title>

For a fresh session with no prior context. Read this, then the files in § Read first,
then continue from § Next steps. Reply in <language>.

## Goal
<1–2 sentences: the objective, not the history.>

## Current state
<What works, what is broken, what is blocked — right now, verifiable. Include
uncommitted-changes summary when the tree is dirty.>

## Done this session
<Short, pointer-like: absolute paths + one-line outcomes. Git recovers the rest.>

## What did NOT work
<Failed approaches with why — verbatim errors. Mandatory: write "none" explicitly
if the session had no dead ends. This is the only section git cannot recover.>

## Key decisions
<Decisions with one-line reasoning, so they are not relitigated. Point to plan/ADR
entries instead of restating them.>

## Next steps
<Ordered. The first step names a concrete file or command — executable within
minutes of cold start. Blocked items name the blocker.>

## Gotchas
<Environment quirks, assumptions, traps discovered this session and not written
anywhere else.>

## Verification status
<claim → evidence (command + outcome) | UNVERIFIED. One line per claim.>

## Git snapshot
<verbatim output of the four commands from step 3>

## Read first
<Ordered list of files the next session must read before acting, with one-line "why" each.>
```

## 4a. Commit and push, then self-check

Run the commit the moment the file is written — a session that dies during the self-check still ships the handoff. First the guard:

```
git -C "<repo>" check-ignore -q "docs/handoffs/<file>"; echo "check-ignore exit: $?"
```

Exit 0 → this repo ignores the path: skip both the commit and the push, and say so in § 5. Exit 1 → trackable, proceed below. Any other exit → git itself failed: skip the commit and the push and report that instead of guessing.

```
git -C "<repo>" add "docs/handoffs/<file>"
git -C "<repo>" commit -m "docs: session handoff <YYYY-MM-DD-HHMM>" -- "docs/handoffs/<file>"
git -C "<repo>" push -u origin HEAD
```

The pathspec bounds the commit to the handoff file, so a dirty tree is never swept in; the push carries whatever else already sits on the current branch — "only its own file" scopes the commit, not the push. `-u origin HEAD` gives a never-pushed branch its upstream instead of aborting. The branch is whatever is checked out, `main` included: the handoff is a technical file, so the `CLAUDE.md` § Git & Workflow PR/merge gate does not reach it and you do not stop to ask.

If the push fails, keep the local commit, skip the push, and report the failure — do not retry in a loop, do not force.

Then check the file against the repo with cheap commands only (git, `ls`, grep — never tests, builds or network) and fix what fails; if that changed the file, run the commit-and-push block again for the same path:

- every path the file mentions exists (`ls`), unless marked deleted or planned;
- § Git snapshot matches `git branch --show-current` and `git status --porcelain` right now, except for the handoff's own commit and its own path appearing in or leaving the dirty list — that drift is expected;
- no "as discussed" / "as mentioned" / "как договорились" and no pronoun without an antecedent in the file;
- the first item of § Next steps names a file or a command.

## 5. Report to the user

Final message (in the user's language): the handoff path, the commit outcome — committed and pushed, or skipped with the guard's reason (path ignored, push failed and the commit is local only) — the claims left UNVERIFIED, and the uncommitted-work reminder when the rest of the tree is dirty.

**Do not hand the user a prompt for the new session** — tell them to open the next session in the same project and run `/pickup-handoff`. Nothing injects the file automatically.

Do not start the new session's work yourself; the handoff is the deliverable.
