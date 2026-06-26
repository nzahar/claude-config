---
name: Agent-Swarm Bbox Labeling With Mandatory Overlay Self-Check
description: Agents drawing YOLO boxes clip target tops / run wide unless forced to render+zoom each box and iterate; sheets scan, full-res labels
type: feedback
---

# Agent-Swarm Bbox Labeling With Mandatory Overlay Self-Check

**Extracted:** 2026-06-26
**Context:** Labeling a detector dataset by fanning out Opus agents over video clips (one agent per clip) to extract frames and draw YOLO bounding boxes, with a human verifying afterward.

## Problem
When an agent estimates a bbox by "looking" at an image and writing coords directly, the boxes are systematically loose — most often the **top edge slides down and clips the target's upper body/fuselage**, and the box **runs wide into empty background** past a faint/blurred edge. The error concentrates on small/low-contrast targets against cluttered backgrounds (where the true extent is ambiguous). A clipped box is worse than a loose one: it excludes part of the real target from the label. Crucially, **the agent cannot see its own error from the coords alone** — two pilot agents on identical task: the one that rendered an overlay and iterated produced tight boxes; the one that wrote coords blind clipped tops.

## Solution
Make a **per-box overlay self-check MANDATORY** in the agent prompt, not optional:
1. Estimate the box, then **render it** (draw the box on the frame via `ffmpeg drawbox`; for small/faint targets also `crop` a region around the box and `scale=...:flags=neighbor` upscale ~4x) and **Read the rendered image back**.
2. Check all four edges: top of fuselage / both wingtips / nose / tail fully inside, no large empty margin. If the top pokes out or an edge is cut → **adjust and re-render. Iterate until tight.**
3. Only then write the label.

Supporting pipeline that makes this cheap at scale:
- **Two-resolution scan:** sample frames at low fps (~2), build **contact sheets** (ffmpeg `tile`) so the agent scans many frames in one Read to *locate* target frames; only Read full-res for the *target* frames to draw boxes.
- **Deterministic tile→index mapping:** tile row-major with a fixed grid (e.g. 6x4) and emit an `index.json` giving `tile(r,c) of sheet NN = first_idx + r*cols + c` plus per-frame timestamps — the agent never guesses which tile is which frame.
- **Validate on a pilot first:** run 3–4 clips (one per data category) end-to-end before the full swarm; eyeball box quality; fold fixes into the swarm prompt. The clip-top-clipping issue only surfaced because a human reviewed pilot overlays.
- **`ffmpeg -nostdin` is required** inside `while read`/loop-driven extraction: ffmpeg otherwise consumes the loop's stdin and silently drops iterations (corrupts batch frame extraction).
- **Idempotent per-item output** (`labels/<stem>/`, `meta/<stem>.json`, with `rm -rf <stem>` at step 0) makes the swarm resumable: a clip is "done" iff its `meta` exists; re-derive the remaining clip list to continue after a limit/crash.
- **Trust-but-reverify triage:** a coarse "no target here" triage pass misses real targets (a clip labeled GROUND held a clear air-to-air target). Re-scan the negative class; don't drop it on triage alone.

## Example
Overlay render + zoom for self-check (box in pixels x,y,w,h):
```
ffmpeg -nostdin -v error -y -i frame.jpg \
  -vf "drawbox=x=429:y=284:w=165:h=44:color=red:thickness=2,crop=340:180:340:220,scale=1360:720:flags=neighbor" \
  -frames:v 1 zoom.jpg
```
Helpers built this session: `tools/dataset/fgb_extract.py` (frames + sheets + index.json), `tools/dataset/fgb_overlay.py` (YOLO labels → box overlays for verify). Both pure stdlib + ffmpeg (no cv2/PIL needed for box draw/verify).

## When to Use
Any time you orchestrate agents/VLMs to produce bounding boxes (detector/segmentation dataset building, auto-annotation, pseudo-label refinement). The single highest-leverage rule: **never let an agent commit a box it hasn't rendered and looked at.** Pair with contact-sheet scanning for cost and a pilot-before-swarm gate for quality.
