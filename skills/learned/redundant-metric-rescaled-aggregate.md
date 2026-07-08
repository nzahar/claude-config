---
name: Redundant Metric Is A Rescaled Aggregate
description: A "new" metric that shares a numerator and divides by an eval-set-constant denominator has an identical %-delta to the one it rescales — zero decision value; stratify instead.
type: feedback
---

# Redundant Metric Is A Rescaled Aggregate

**Extracted:** 2026-07-08
**Context:** Designing evaluation metrics to compare models/runs; tempted to add a second "normalized" aggregate for extra insight.

## Problem
A metric that is a **fixed rescaling** of an existing one carries **zero** additional decision value. Example: `bits_per_event = total_NLL / n_events` vs `bits_per_patient_day = total_NLL / Σ_days`. Both share the numerator (total held-out NLL) and their denominators are **fixed properties of the eval set** — identical across the models being compared. So `metricB / metricA = n_events / Σ_days = const`, and the **%-delta vs baseline is mathematically identical** for both. The "new" metric cannot disagree with the one it rescales. (Same trap makes `val_loss`, aggregate `bits_per_event`, and any `total_NLL / const` all carry the same %-delta.)

## Solution
Before adding a metric, ask: **does it change the numerator, or only rescale by an eval-set constant?** Discriminative power comes from **stratification** — splitting the numerator into subgroups whose deltas can *diverge* (per-class, per-time-bucket, per-slice) — not from choosing a different global denominator. Prefer a stratified breakdown (e.g. per-`code_system`, per-gap-bucket) over a rescaled aggregate; the breakdown can reveal a masked gain (a large near-deterministic subgroup diluting the aggregate) that no rescaling can.

## Example
- Redundant: `bits_per_patient_day` next to `bits_per_event` — dropped.
- Useful: `bits_per_event` **stratified by subgroup** — non-redundant, un-masks a subgroup where the aggregate is flat but the signal is real.

## When to Use
Metric design for model/run comparison; whenever a stakeholder asks "shouldn't we also track <normalized-thing>?". A one-line ratio check (`is the extra denominator a fixed eval-set constant?`) settles whether it adds anything.
