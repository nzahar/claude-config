---
name: PyTorch Ablation Init RNG Shift
description: Adding a submodule (even "last") before self.apply() shifts the shared-param init RNG — breaks same-seed comparability across model variants; construct axis modules AFTER apply().
type: feedback
---

# PyTorch Ablation Init RNG Shift

**Extracted:** 2026-07-08
**Context:** Comparing model variants at the same seed (ablations, single-axis experiments) where one variant adds an extra module — e.g. a new conditioning embedding/head.

## Problem
You claim "variant B differs from variant A only by the added module, same seed → same shared weights." It's false by default. `nn.Embedding(...)` / `nn.Linear(...)` construction calls `reset_parameters()` → `nn.init.*`, which draws from the **global default RNG**. So merely *constructing* the extra module (even "registered last") **before** `self.apply(self._init_weights)` advances the RNG stream that `apply()` then uses to (re)initialize the **shared** params (tok/pos/blocks/head). Result: the shared weights differ across variants at the same seed → the "single-axis" comparison is confounded by a full random re-init of every shared weight. A §4.5 review caught this only after a run had launched; cost a restart.

## Solution
Construct the variant-specific modules **AFTER** `self.apply(...)` and initialize them explicitly:

```python
# shared modules first
self.tok_emb, self.pos_emb, self.blocks, self.lm_head = ...
if tie: self.lm_head.weight = self.tok_emb.weight
self.apply(self._init_weights)          # shared params — RNG independent of the extra module
# axis-specific module AFTER apply(), explicit init
self.axis_emb = nn.Embedding(k, d) if variant else None
if self.axis_emb is not None:
    nn.init.normal_(self.axis_emb.weight, mean=0.0, std=0.02)
```

Now `apply()` only ever traverses the shared modules with the same RNG state whether or not the extra module exists → shared init is byte-identical across variants at the same seed.

## Example
Verify before spending compute (seconds on the target box):
```python
def mk(pe): set_seed(1337); return Model(replace(cfg, variant=pe))
shared = lambda m: {k:v for k,v in m.state_dict().items() if not k.startswith(("axis_emb",))}
a, b = shared(mk("base")), shared(mk("variant"))
assert all(torch.equal(a[k], b[k]) for k in a)   # must be True after the fix
```

## When to Use
Any time you add/remove an `nn.Module` and want same-seed init parity across model variants: ablations, single-axis experiments, adding an embedding/adapter/head, "only-difference-is-X" comparability claims. Note "registered last" / traversal-order reasoning is necessary but NOT sufficient — the fix is construction *after* `apply()` + explicit init.
