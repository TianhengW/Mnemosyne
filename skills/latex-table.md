---
name: latex-table
description: Convert experiment results to publication-quality LaTeX tables
---

# LaTeX Table Generator

Convert experiment results (CSV, JSON, dict, or raw data) into publication-quality LaTeX tables.

## Instructions

1. Accept data in any format (CSV, JSON, Python dict, raw numbers)
2. Generate a clean LaTeX table with:
   - Bold best results per column
   - Proper alignment
   - Horizontal rules (booktabs style)
   - Optional: underline second-best, ± std notation

## Table Templates

### Standard Results Table
```latex
\begin{table}[t]
\centering
\caption{Comparison on [Benchmark]. Best results in \textbf{bold}, second best \underline{underlined}.}
\label{tab:main_results}
\resizebox{\columnwidth}{!}{%
\begin{tabular}{l|cccc}
\toprule
Method & Metric1 $\uparrow$ & Metric2 $\uparrow$ & Metric3 $\downarrow$ & Metric4 $\uparrow$ \\
\midrule
Baseline1 & 72.3 & 65.1 & 0.42 & 81.2 \\
Baseline2 & 74.1 & 67.8 & 0.38 & 83.5 \\
\midrule
\textbf{Ours} & \textbf{78.6} & \textbf{71.2} & \textbf{0.31} & \textbf{87.3} \\
\bottomrule
\end{tabular}%
}
\end{table}
```

### Ablation Table
```latex
\begin{table}[t]
\centering
\caption{Ablation study on [Dataset].}
\label{tab:ablation}
\begin{tabular}{ccc|cc}
\toprule
Comp. A & Comp. B & Comp. C & Acc. & F1 \\
\midrule
\ding{55} & \ding{55} & \ding{55} & 68.2 & 65.1 \\
\ding{51} & \ding{55} & \ding{55} & 72.4 & 69.3 \\
\ding{51} & \ding{51} & \ding{55} & 75.1 & 72.8 \\
\ding{51} & \ding{51} & \ding{51} & \textbf{78.6} & \textbf{76.2} \\
\bottomrule
\end{tabular}
\end{table}
```

### Multi-Dataset Table
```latex
\begin{table*}[t]
\centering
\caption{Results across multiple benchmarks.}
\label{tab:multi_dataset}
\begin{tabular}{l|cc|cc|cc}
\toprule
\multirow{2}{*}{Method} & \multicolumn{2}{c|}{Dataset A} & \multicolumn{2}{c|}{Dataset B} & \multicolumn{2}{c}{Dataset C} \\
& Acc & F1 & Acc & F1 & Acc & F1 \\
\midrule
Method1 & 72.3±0.5 & 69.1±0.8 & 81.2±0.3 & 78.5±0.6 & 65.8±1.2 & 62.3±1.5 \\
\textbf{Ours} & \textbf{76.8±0.4} & \textbf{74.2±0.6} & \textbf{84.5±0.2} & \textbf{82.1±0.4} & \textbf{70.3±0.9} & \textbf{67.8±1.1} \\
\bottomrule
\end{tabular}
\end{table*}
```

## Formatting Rules
- Use `booktabs` package (toprule, midrule, bottomrule)
- Never use vertical lines (`|` only for logical grouping if needed)
- Align decimal points when possible
- Use `$\uparrow$` / `$\downarrow$` to indicate metric direction
- Include std (±) for results across multiple seeds
- Bold the BEST result; optionally underline second best
- Use `\resizebox{\columnwidth}{!}{...}` if table is too wide

## From Data to Table

When given raw data:
```python
# Input format
results = {
    "Method A": {"acc": 72.3, "f1": 69.1},
    "Method B": {"acc": 74.5, "f1": 71.8},
    "Ours": {"acc": 78.6, "f1": 76.2},
}
# → Generate LaTeX with bold best values
```

## Required Packages
```latex
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{pifont}  % for \ding{51} \ding{55}
```
