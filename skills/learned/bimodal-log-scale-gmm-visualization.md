# Bimodal Distribution Visualization: Log Scale + GMM

**Extracted:** 2026-03-30
**Context:** Plotting histograms of lab/biomarker data that spans multiple orders of magnitude with two natural clusters

## Problem

When data has two clusters at very different scales (e.g., PSA values: cluster 1 ≈ 0.04 ng/mL, cluster 2 ≈ 15 ng/mL), a linear histogram is useless — the dominant cluster at near-zero crushes everything else into a thin spike. Clipping the axis to remove outliers doesn't help either because the two humps remain overlapping.

## Solution

1. **Log-transform** the data: `psa_log = np.log10(values + epsilon)` (epsilon avoids log(0))
2. **Fit GMM** with 2 components on the log-transformed data
3. **Plot histogram** with equal-width bins in log space
4. **Overlay GMM components** individually (fill + line), skip the sum line
5. **Restore original-unit tick labels** so the axis is readable

## Example

```python
from sklearn.mixture import GaussianMixture
from scipy.stats import norm
import numpy as np

epsilon = 0.01  # avoids log(0) for near-zero values
data_log = np.log10(data + epsilon)

gmm = GaussianMixture(n_components=2, random_state=42)
gmm.fit(data_log.values.reshape(-1, 1))

x_log = np.linspace(data_log.min(), data_log.max(), 500)
weights = gmm.weights_
means   = gmm.means_.flatten()
stds    = np.sqrt(gmm.covariances_.flatten())

fig, ax = plt.subplots(figsize=(12, 5), facecolor='white')
ax.set_facecolor('white')

bins_log = np.linspace(data_log.min(), data_log.max(), 70)
ax.hist(data_log, bins=bins_log, color='#BDC3C7', edgecolor='white',
        linewidth=0.3, density=True, label='Distribution (density)')

colors = ['#27AE60', '#E74C3C']
for i, (w, m, s) in enumerate(zip(weights, means, stds)):
    comp = w * norm.pdf(x_log, m, s)
    center = round(10**m - epsilon, 2)
    ax.fill_between(x_log, comp, alpha=0.25, color=colors[i])
    ax.plot(x_log, comp, color=colors[i], linewidth=1.8,
            label=f'Cluster {i+1}: center ≈ {center}  ({w*100:.0f}%)')

# Restore human-readable tick labels in original units
tick_vals = [0.01, 0.1, 0.5, 1, 2, 4, 10, 20, 50, 100]
ax.set_xticks([np.log10(v + epsilon) for v in tick_vals])
ax.set_xticklabels([str(v) for v in tick_vals])

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.legend()
plt.tight_layout()
```

## When to Use

- Any continuous variable that spans 2+ orders of magnitude (lab values, prices, counts, durations)
- When you visually expect two populations but a linear histogram shows only one dominant spike
- When the user says "make the two humps visible" or "the chart looks unclear"

## Notes

- Choose `epsilon` based on the minimum meaningful value in your domain (0.01 for PSA ng/mL)
- Skip plotting the GMM sum line — it adds visual noise without insight
- `n_components=2` is appropriate when you have a known biological/domain reason for two groups; use BIC/AIC selection otherwise
- Tick values should cover the actual data range; adjust `tick_vals` accordingly
