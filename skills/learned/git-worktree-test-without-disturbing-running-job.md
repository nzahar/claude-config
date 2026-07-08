---
name: Git Worktree To Test A Branch Without Disturbing A Running Job
description: To run tests/a repro on branch B on a box whose main checkout is on branch A running a long job, use git worktree (separate dir), never git checkout.
type: feedback
---

# Git Worktree To Test A Branch Without Disturbing A Running Job

**Extracted:** 2026-07-08
**Context:** A remote box's main checkout is on branch A running a long job (e.g. training); you need to run tests / a repro / a build on a different branch B on that same box.

## Problem
`git checkout B` in the box's main checkout switches the working tree **under** the running job, and re-reads/overwrites tracked files. It also moves `HEAD`, which can corrupt provenance that reads `git rev-parse` (e.g. a run recording its own `git_sha`).

## Solution
Use a **linked worktree** — a separate working directory for branch B — and remove it after:

```bash
git -C $REPO fetch origin -q
git -C $REPO worktree add -q --detach $WT origin/feature/branch-B
cd $WT && python -m pytest ...        # or the repro
git -C $REPO worktree remove --force $WT
```

The main checkout's `HEAD` and files are untouched; the running job is unaffected. Put `$WT` inside the box's allowed/encrypted mount if it has a data-perimeter rule (not `/tmp` if that violates it).

## Example
Belt-and-suspenders reasoning worth stating to a nervous user: a launched Python process holds its code **in memory** from import time, so it is robust to on-disk file changes anyway (it only re-reads config at start / manifest at end). The worktree means you don't even rely on that — and it keeps the running job's `git_sha` provenance intact.

## When to Use
Verifying/testing a different branch on a machine mid-run on another branch; CI-style checks on a shared box; any time you must not perturb a working tree a live process or teammate depends on. CPU-only tests won't contend with the running job's GPU.
