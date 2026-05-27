---
name: plot-figure
description: Generate publication-quality figures with matplotlib/seaborn
---

# Publication Figure Generator

Generate publication-quality figures suitable for top-tier venues (NeurIPS, ICML, ICLR, CVPR).

## Instructions

1. Understand the data and what story the figure should tell
2. Choose the appropriate plot type
3. Generate matplotlib/seaborn code following publication standards
4. Apply consistent styling

## Style Standards

```python
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
import numpy as np

# Publication defaults
plt.rcParams.update({
    'font.size': 10,
    'font.family': 'serif',
    'font.serif': ['Times New Roman'],
    'axes.labelsize': 11,
    'axes.titlesize': 11,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'lines.linewidth': 1.5,
    'lines.markersize': 5,
})

# Color palettes (colorblind-friendly)
COLORS = ['#2196F3', '#F44336', '#4CAF50', '#FF9800', '#9C27B0', '#795548']
# Or use: sns.color_palette("colorblind")
```

## Figure Size Guide (inches)

| Venue | Single Column | Double Column | 
|-------|--------------|---------------|
| NeurIPS/ICML | 5.5 × 3.5 | 5.5 × 2.5 (subplot) |
| CVPR/ICCV | 3.25 × 2.5 | 6.875 × 3.0 |
| ICLR | 5.5 × 3.5 | 5.5 × 2.5 |

## Common Plot Types

### Training Curves
```python
fig, ax = plt.subplots(figsize=(5.5, 3.5))
for method, data in results.items():
    mean = np.mean(data, axis=0)
    std = np.std(data, axis=0)
    ax.plot(steps, mean, label=method)
    ax.fill_between(steps, mean - std, mean + std, alpha=0.2)
ax.set_xlabel('Training Steps')
ax.set_ylabel('Loss')
ax.legend(frameon=True, fancybox=False, edgecolor='black')
plt.tight_layout()
```

### Bar Chart (Method Comparison)
```python
fig, ax = plt.subplots(figsize=(5.5, 3.0))
x = np.arange(len(datasets))
width = 0.2
for i, (method, scores) in enumerate(results.items()):
    ax.bar(x + i * width, scores, width, label=method, color=COLORS[i])
ax.set_xticks(x + width)
ax.set_xticklabels(datasets)
ax.set_ylabel('Accuracy (%)')
ax.legend()
```

### Ablation Heatmap
```python
fig, ax = plt.subplots(figsize=(4, 3))
sns.heatmap(data, annot=True, fmt='.1f', cmap='RdYlGn', ax=ax,
            xticklabels=cols, yticklabels=rows)
ax.set_xlabel('Component')
ax.set_ylabel('Setting')
```

## Checklist Before Saving
- [ ] Axis labels are descriptive (not variable names)
- [ ] Legend doesn't overlap data
- [ ] Font sizes are readable when printed
- [ ] Colors are distinguishable in grayscale
- [ ] Grid is subtle (alpha=0.3)
- [ ] No unnecessary chartjunk
- [ ] Consistent style across all figures in the paper
- [ ] Saved as both PDF (for paper) and PNG (for slides)
