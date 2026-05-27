---
name: ablation-plan
description: Design ablation study matrix and generate batch experiment scripts
---

# Ablation Study Planner

Design rigorous ablation experiments and generate scripts to run them systematically.

## Instructions

1. Identify the method's components to ablate
2. Design the ablation matrix (which combinations to test)
3. Generate batch running scripts
4. Plan the results presentation (table/figure format)

## Ablation Design Principles

### What to Ablate
- Each novel component of your method
- Key hyperparameters
- Design choices (architecture, loss terms, augmentation)
- Input modalities / feature sources

### Types of Ablation

**1. Component Ablation (most common)**
Remove or replace one component at a time:
```
Full model: A + B + C + D → result
-A: B + C + D → shows A's contribution
-B: A + C + D → shows B's contribution  
-C: A + B + D → shows C's contribution
-D: A + B + C → shows D's contribution
```

**2. Incremental Ablation**
Build up from baseline:
```
Baseline → +A → +A+B → +A+B+C → Full (ours)
```

**3. Substitution Ablation**
Replace your component with alternatives:
```
Ours (with X) vs. replace X with {X1, X2, X3}
```

**4. Hyperparameter Sensitivity**
Vary key hyperparams:
```
λ ∈ {0.01, 0.1, 0.5, 1.0, 5.0}
```

## Generating Experiment Configs

```python
# ablation_configs.py
import itertools
from pathlib import Path
import yaml

BASE_CONFIG = {
    "model": "full",
    "use_component_a": True,
    "use_component_b": True,
    "use_component_c": True,
    "lr": 1e-4,
    "epochs": 100,
    "seed": 42,
}

ABLATIONS = {
    "no_comp_a": {"use_component_a": False},
    "no_comp_b": {"use_component_b": False},
    "no_comp_c": {"use_component_c": False},
    "no_comp_ab": {"use_component_a": False, "use_component_b": False},
}

SEEDS = [42, 123, 456]  # Multiple seeds for significance

def generate_configs():
    configs = []
    for name, overrides in ABLATIONS.items():
        for seed in SEEDS:
            config = {**BASE_CONFIG, **overrides, "seed": seed}
            config["exp_name"] = f"{name}_seed{seed}"
            configs.append(config)
    return configs

if __name__ == "__main__":
    Path("configs/ablation").mkdir(parents=True, exist_ok=True)
    for config in generate_configs():
        path = f"configs/ablation/{config['exp_name']}.yaml"
        with open(path, 'w') as f:
            yaml.dump(config, f)
        print(f"Generated: {path}")
```

## Batch Submission Script
```bash
#!/bin/bash
# run_ablation.sh - Submit all ablation experiments

CONFIGS_DIR="configs/ablation"
LOG_DIR="logs/ablation"
mkdir -p $LOG_DIR

for config in $CONFIGS_DIR/*.yaml; do
    name=$(basename $config .yaml)
    sbatch \
        --job-name="abl_${name}" \
        --output="${LOG_DIR}/${name}.out" \
        --gres=gpu:1 \
        --time=12:00:00 \
        --wrap="python train.py --config $config --output_dir outputs/ablation/$name"
    echo "Submitted: $name"
    sleep 1  # Avoid overwhelming scheduler
done
```

## Results Aggregation
```python
# collect_ablation_results.py
import json
from pathlib import Path
import pandas as pd

results = []
for exp_dir in Path("outputs/ablation").iterdir():
    metrics_file = exp_dir / "metrics.json"
    if metrics_file.exists():
        metrics = json.loads(metrics_file.read_text())
        metrics["experiment"] = exp_dir.name
        results.append(metrics)

df = pd.DataFrame(results)
# Group by ablation type (aggregate over seeds)
summary = df.groupby(df['experiment'].str.rsplit('_seed', n=1).str[0]).agg(['mean', 'std'])
print(summary.to_markdown())
```

## Tips
- Always run with multiple seeds (≥3) for statistical validity
- Include the full model run with same seeds for fair comparison
- Record wall-clock time to show efficiency trade-offs
- Design ablations to answer a specific question the reviewer would ask
- Present results as a table AND a bar chart for visual impact
