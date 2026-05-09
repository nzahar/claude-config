---
name: Matplotlib Dark Jupyter Theme Override Fix
description: Fix invisible matplotlib text and black legend boxes in dark Jupyter themes — set rcParams before plotting, not per-call colors
type: feedback
---

# Matplotlib Dark Jupyter Theme Override Fix

**Extracted:** 2026-03-27
**Context:** Jupyter notebooks with dark UI themes (JupyterLab dark, VSCode dark) where matplotlib figures render with invisible/white text, black legend boxes, and missing axis labels when saved to PNG.

## Problem

Dark notebook themes override matplotlib's default colors at the renderer level. Symptoms appear progressively — each render reveals a new broken element:
1. Axis labels invisible (white text on white background in saved PNG)
2. Tick numbers invisible
3. Legend appears as a solid black rectangle
4. Legend text invisible

Setting colors in `ax.set_xlabel(color='black')` alone is insufficient — the theme overrides at the rcParams level first.

## Solution

Three-layer defense required — all three are needed:

```python
import matplotlib
import matplotlib.pyplot as plt

# Layer 1: rcParams — must come BEFORE fig/ax creation
matplotlib.rcParams.update({
    'axes.labelcolor':   'black',
    'xtick.color':       'black',
    'ytick.color':       'black',
    'text.color':        'black',
    'axes.edgecolor':    'black',
    'legend.facecolor':  'white',
    'legend.edgecolor':  '#cccccc',
    'legend.labelcolor': 'black',
})

fig, ax = plt.subplots(...)
fig.patch.set_facecolor('white')   # figure background
ax.set_facecolor('#F7F9FC')        # axes background (light, not white)

# Layer 2: explicit color on every text element
ax.set_xlabel('...', fontsize=13, color='black', labelpad=12)
ax.set_ylabel('...', fontsize=13, color='black', labelpad=12)
ax.set_title('...', fontsize=13, color='black')
ax.set_xticklabels([...], color='black')
ax.set_yticklabels([...], color='black')

# Layer 3: explicit legend frame styling after creation
leg = ax.legend(...)
leg.get_frame().set_facecolor('white')
leg.get_frame().set_alpha(1.0)
leg.get_frame().set_edgecolor('#cccccc')
for text in leg.get_texts():
    text.set_color('black')

# Always save with explicit facecolor
fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='white')
```

## When to Use

- Any matplotlib figure in a Jupyter notebook with a dark UI theme
- When axis labels or legend are invisible in saved PNG but visible inline
- When legend background is black or legend text is white
- Anytime `fig.savefig` output looks different from `plt.show()` inline output

## Notes

- `bbox_inches='tight'` + external legend (`bbox_to_anchor`) causes `tight_layout` to crop axis labels — move legend inside axes instead (`loc='upper left'`)
- `plt.style.use('default')` is the nuclear option if the above fails — resets everything but may change aesthetics
