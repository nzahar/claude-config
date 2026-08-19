---
name: Near-Singular Endgame Metric Artifact — Bin Against Progress, Read Off the Singularity
description: A metric read where its denominator →0 (angle at CPA, ratio near zero range) fabricates run-to-run scatter; bin against a monotone progress var to localize, read at a fixed offset to fix.
type: feedback
---

# Near-Singular Endgame Metric Artifact — Bin Against Progress, Read Off the Singularity

**Extracted:** 2026-07-18
**Context:** A per-run scalar (approach angle, impact geometry, a ratio) scatters wildly run-to-run and you suspect the underlying process is broken — but the process may be fine and the METRIC is sampling a geometric singularity.

## Problem
A guidance metric — terminal LOS elevation `atan2(Δz, hypot(Δx,Δy))` read as a 0.15 s median at closest approach — scattered 23° across nominally-identical runs. The instinct was "the controller is non-deterministic / the fix regressed." Two dead-end sessions chased the controller. The real cause: at closest approach the horizontal range → 0, so a **sub-meter, physically-uncontrolled cross-track subtends tens of degrees** — the metric was reading `atan2` in its near-singular regime, where trajectory noise far below the deliverable's resolution gets amplified into a huge apparent spread. The trajectory itself was reproducible to ≤1.5°.

## Solution
Two moves, in order:

1. **Diagnose by binning the metric against a monotone progress variable** (slant range, time-to-go, phase), not against run index. Build a table of the quantity's std at fixed progress checkpoints. Here: std @40 m = 0.3°, @20 m = 0.9°, @10 m = 1.5°, @5 m = 3.2°, @2 m = 44°. The instant that table blows up only at the tail, you know the process is reproducible and the scatter is manufactured in the endgame — a metric/singularity problem, not a process problem.

2. **Fix by reading the metric at a fixed reference offset from the singularity** — a fixed range band (e.g. 8–12 m), a fixed t_go, not "at the event." The physically-faithful value lives where the denominator is still well-conditioned. Re-scoring collapsed the 23° spread to 5°, all in the target band. Return `None` (don't fabricate from a distant frame) when the trajectory never reaches the band, so a genuine large-miss isn't masked as in-band.

## Example
```python
# BAD: reads the angle in the near-singular window ending at CPA/impact
def approach_angle(rel, t_end, window_s=0.15):
    los = [degrees(atan2(r[2], hypot(r[0], r[1])))
           for t, r in rel if t_end - window_s <= t <= t_end]   # hypot -> 0 here
    return median(los)

# GOOD: read over a fixed slant-range band, off the singularity
def approach_angle_at_range(rel, t_end, band_m=(8.0, 12.0)):
    lo, hi = band_m
    los = [degrees(atan2(r[2], hypot(r[0], r[1])))
           for t, r in rel if t <= t_end and lo <= sqrt(r[0]**2+r[1]**2+r[2]**2) <= hi]
    return median(los) if los else None   # None, not a fabricated value, when never close

# DIAGNOSTIC that proved it was the metric, not the process:
for R in (40, 30, 20, 10, 5, 3, 2):
    print(R, stdev(los_elevation_at_slant_range(tr, R) for tr in traces))  # blows up only at the tail
```

## When to Use
- A per-run outcome (angle, ratio, decomposed component) scatters and you're about to blame the controller / model / a recent change for non-determinism.
- The metric involves a division or `atan2` whose denominator (range, closing distance, a count) approaches zero at the measurement instant (CPA, impact, t_go→0, end-of-run).
- Before escalating "it's non-reproducible": **bin the quantity against a monotone progress variable and check whether the variance is uniform or tail-concentrated.** Tail-concentrated ⇒ read at a fixed offset from the singularity.
- Sibling of the post-event-data corruption class (reading a kinetic metric after collision): both are "read the metric at the wrong point on the trajectory." Same fix family: pick a well-conditioned reference point, not the event.
