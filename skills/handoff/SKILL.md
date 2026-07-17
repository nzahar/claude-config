---
name: handoff
description: "Write a session handoff file so a fresh session can cold-start the current work, and have it reviewed by handoff-reviewer. Invoke when the user types /handoff [fast] [optional focus], or asks to prepare a handoff for a new session (context nearly full, wrapping up with continuation expected). The file is single-use: the SessionStart hook injects it into the next session and consumes it. NOT a commit/push command — it never touches git state."
argument-hint: "[fast] [focus]"
---

# /handoff — session handoff with review

You are wrapping the current session's state into a file a fresh session can act on with zero conversation history. The handoff is judged by one criterion: **can the next session continue safely using only this file and the repo?** Write it while you still can — a handoff authored at 95% context is authored by a degraded session; do not defer the invocation.

## 1. Parse the invocation

`/handoff [fast] [focus]`

- **fast** — skip the review step. Use when context is nearly exhausted.
- **focus** (optional free text) — what the user wants emphasized (e.g. a specific bug, a subtask); weave it into Goal / Next steps, do not add sections.

## 2. Resolve the target path

One file per project. Ask the script — it prints the full path and nothing else:

```
"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks/handoff-path.sh" <session's working directory>
```

Write to exactly the path it printed. **Never construct that path yourself** — not the directory, not the filename. The hook that injects the handoff calls this same script; a path that differs by one character means the hook looks where nothing was written and silently injects nothing, and the whole feature no-ops with no signal to anyone.

Pass the session's working directory — the one named in your environment context — as a literal absolute path. Do **not** substitute `$(pwd)` or `$(git rev-parse --show-toplevel)`: those evaluate in the Bash tool's cwd, which persists across calls and may have been moved into another repository. The hook resolves the path from the session's real cwd, so if the tool's cwd has drifted, a `pwd`-derived path is one the hook will never look at.

If the script prints nothing or fails, **stop and tell the user the handoff path cannot be resolved.** Do not guess a path — a guessed path is a file nothing will ever inject.

The file lives outside the project on purpose — it never reaches the project's git. If the path already exists (a second `/handoff` in one session), **read it first and update it** — carry forward still-valid content, especially What did NOT work. Otherwise the previous handoff is not there to read: the hook consumed it at session start and moved it to `handoffs/_archive/`; its content is already in your context, so carry it forward from there.

## 3. Collect the git snapshot mechanically

Run and capture verbatim (do not paraphrase, do not summarize):

```
git branch --show-current
git status --porcelain
git log --oneline -5
git diff --name-only
```

This block goes into § Git snapshot as-is. The deterministic part of the handoff is trustworthy by construction; only the narrative needs review.

## 4. Write the handoff

Use the template below. Constraints (the reviewer mechanically checks these, except the two marked "on you"):

- **English** (documentation), with the reply-language line in the header (e.g. "Reply in Russian") — on you, the reviewer does not check language.
- **Narrative ≤ ~1000 words** (excluding § Git snapshot and fenced blocks). Budget forward: Next steps and What did NOT work outrank history — git recovers finished work, dead ends are irrecoverable.
- **Absolute paths** for every file mentioned — on you, the reviewer checks existence, not absoluteness.
- **Error messages verbatim**, never paraphrased.
- **Self-contained**: no "as discussed", no references to the conversation, no unresolved pronouns. Every referent resolves within the file.
- **Pointers, not duplicates**: link STATE.md, codemaps, plan files, ADRs — do not restate their content.
- **Claims carry evidence**: anything asserted as done/passing names the command and its outcome in § Verification status. What you did not verify this session, mark unverified — honesty beats optimism; the next session re-checks before trusting.
- If `git status --porcelain` is non-empty, § Current state must say what the uncommitted changes are — they are invisible to the next session's `git log`. Remind the user (outside the file) that uncommitted work is at risk; **never commit yourself**.

## Handoff template

Canonical section list — `handoff-reviewer` H5 reads this section; changing it changes what every review requires. Load-bearing sections (missing one is a reviewer `blocker`; a missing non-load-bearing section is a `warning`): **What did NOT work**, **Next steps**, **Git snapshot** — the irrecoverable / cold-start-critical ones.

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

## 5. Review

Unless the user passed `fast`, dispatch `handoff-reviewer` with the **explicit file path** in the prompt (it refuses to guess). It is read-only and fast (git + filesystem checks only).

One run, no loop: fix every blocker and warning it returns, then stop. Surface its `needs-verification` list to the user — those are the claims the next session must re-check before trusting.

## 6. Report to the user

Final message (in the user's language): the handoff path, the reviewer verdict (or that review was skipped in `fast` mode), and the uncommitted-work reminder when the tree is dirty.

**Do not hand the user a prompt for the new session** — the SessionStart hook injects the handoff automatically and consumes it, so the next session starts with it already in context. Just say where the file is.

The hook needs `jq`. If `command -v jq` finds nothing, say so plainly: the file is written but nothing will inject it, and the user must read it into the next session themselves.

Do not start the new session's work yourself; the handoff is the deliverable.
