---
name: stat-test
description: Statistical significance testing for experiment results
---

# Statistical Significance Testing

Perform proper statistical tests on experiment results to validate claims and survive reviewer scrutiny.

## Instructions

When the user has results from multiple runs/seeds:
1. Determine the appropriate test
2. Generate the code to run it
3. Interpret the results
4. Suggest how to report in the paper

## Decision Tree: Which Test?

```
Are you comparing two methods?
├── Yes → Are results paired (same test set)?
│   ├── Yes → Paired t-test (or Wilcoxon signed-rank if non-normal)
│   └── No  → Independent t-test (or Mann-Whitney U)
└── No (3+ methods) → ANOVA + post-hoc (or Friedman + Nemenyi)

Are results from different random seeds?
├── Yes → Use all seed results as samples
└── No (single run) → Bootstrap confidence intervals
```

## Implementation

### Basic: Multiple Seeds Comparison
```python
import numpy as np
from scipy import stats

# Results from 5 seeds
method_a = np.array([76.2, 75.8, 76.5, 76.0, 76.3])  # accuracies
method_b = np.array([74.1, 74.5, 73.8, 74.2, 74.0])

# Paired t-test (same seeds, same data splits)
t_stat, p_value = stats.ttest_rel(method_a, method_b)
print(f"Paired t-test: t={t_stat:.3f}, p={p_value:.4f}")

# Effect size (Cohen's d)
diff = method_a - method_b
cohens_d = diff.mean() / diff.std()
print(f"Cohen's d: {cohens_d:.3f}")

# Report: "Our method significantly outperforms baseline 
#          (p < 0.01, paired t-test, 5 seeds)"
```

### Bootstrap Confidence Intervals
```python
def bootstrap_ci(scores, n_bootstrap=10000, ci=0.95):
    """Compute bootstrap confidence interval for a single run."""
    n = len(scores)
    bootstrap_means = []
    for _ in range(n_bootstrap):
        sample = np.random.choice(scores, size=n, replace=True)
        bootstrap_means.append(sample.mean())
    
    lower = np.percentile(bootstrap_means, (1 - ci) / 2 * 100)
    upper = np.percentile(bootstrap_means, (1 + ci) / 2 * 100)
    return lower, upper

# Per-sample scores from evaluation
scores = np.array([...])  # per-example accuracy
lower, upper = bootstrap_ci(scores)
print(f"95% CI: [{lower:.2f}, {upper:.2f}]")
```

### Multiple Comparisons (3+ methods)
```python
from scipy.stats import friedmanchisquare
import scikit_posthocs as sp  # pip install scikit-posthocs

# Results: rows = seeds, columns = methods
results = np.array([
    [76.2, 74.1, 73.5, 72.8],  # seed 1
    [75.8, 74.5, 73.2, 73.1],  # seed 2
    [76.5, 73.8, 74.0, 72.5],  # seed 3
    [76.0, 74.2, 73.8, 72.9],  # seed 4
    [76.3, 74.0, 73.6, 73.0],  # seed 5
])
method_names = ["Ours", "Baseline1", "Baseline2", "Baseline3"]

# Friedman test (non-parametric ANOVA for repeated measures)
stat, p = friedmanchisquare(*results.T)
print(f"Friedman test: χ²={stat:.3f}, p={p:.4f}")

# Post-hoc: Nemenyi test
nemenyi = sp.posthoc_nemenyi_friedman(results)
print(nemenyi)
```

### Reporting in Paper

**In-text:**
> Our method achieves 76.2±0.3% accuracy, significantly outperforming the best baseline (74.1±0.3%, p < 0.01, paired t-test across 5 random seeds).

**In table:**
```
Method     | Acc (%)
-----------|---------
Baseline1  | 74.1 ± 0.3
Baseline2  | 73.6 ± 0.3
Ours       | 76.2 ± 0.3*

* p < 0.01 vs all baselines (paired t-test, 5 seeds)
```

## Common Reviewer Questions

**"Are the improvements statistically significant?"**
→ Report p-value from paired t-test + number of seeds

**"What's the variance across runs?"**
→ Report mean ± std, or confidence intervals

**"Did you use the same data splits?"**
→ Yes → paired test; No → independent test + report this

**"Only 3 seeds?"**
→ 5 seeds is the community standard. If compute-limited, use bootstrap CI.

## Tips
- Always use ≥5 seeds for the main result
- Use the SAME seeds across all methods for fair comparison
- Report both mean±std AND p-values
- For expensive experiments (LLM training), 3 seeds + bootstrap is acceptable
- Don't p-hack: decide on the test BEFORE running experiments
- If p > 0.05, be honest — say "comparable" not "better"
