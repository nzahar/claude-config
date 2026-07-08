---
name: Single-GPU Staged Hypothesis Auto-Launch
description: Keep a single-GPU research loop busy by staging the next hypothesis (code+review+config) ahead and auto-launching the right one when the card frees, per a pre-registered verdict rule.
type: feedback
---

# Single-GPU Staged Hypothesis Auto-Launch

**Extracted:** 2026-07-08
**Context:** Iterative single-GPU (or single-slot) experiment loops where a run finished and the card sat idle until a human launched the next one.

## Problem
On one GPU, runs serialize: the next run can only start when the current one frees the card — which is exactly when the current run's **verdict is already known**. So "designing the next hypothesis in advance, blind of the result" buys **zero** wall-clock. The real loss is a finished run leaving the card idle overnight because nobody launched the next.

## Solution
Optimize for *utilization*, not for pre-deciding the axis:

1. **Prep only code-requiring next hypotheses.** Config-only axes (LR, size, context-len) need nothing but a `config.yaml` at launch — don't pre-build them.
2. **Stage a ready-to-fire config per verdict branch** (keep → hypothesis X vs the new champion; kill → fallback Y vs the old anchor). Commit both; only one launches.
3. **Auto-launch on GPU-free**: the monitor (already polling) detects completion, applies a **pre-registered decision rule** (verdict → which staged config), and launches — smoke then run. No human in the loop overnight.
4. **Keep the monitor session alive** (its scheduled wakeups carry the launch logic + pid + paths), and **externalize the essentials** (pushed branches, staged configs, the decision rule embedded in the wakeup prompt) so a session death loses only the automation, never the work — a fresh session resumes with `pull → smoke → run`.

## Example
Decision rule baked into the monitor: `keep|refine → git pull H_next branch + GPU smoke + nohup run vs new champion; kill → launch config-only fallback vs prior anchor; ambiguous → ping human`. Cloud cron is the wrong tool here — a headless cron lacks the SSH/VPN to reach the box; a self-rescheduling wakeup that resumes the *current* environment does have it.

## When to Use
Long-running, serialized experiment loops (single GPU / single runner) where throughput matters and you want the hardware busy without babysitting. Especially: overnight/unattended stretches, research hypothesis loops with keep/kill verdicts.
