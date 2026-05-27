---
name: exp-config
description: Manage experiment configurations, compare runs, track hyperparameters
---

# Experiment Config Manager

Manage experiment configurations systematically — create, compare, and track hyperparameters across runs.

## Instructions

1. When starting a new experiment: help structure the config
2. When comparing runs: diff configs to identify what changed
3. When results differ: trace back to config differences
4. Maintain a config registry in Obsidian

## Config Structure Standard

```yaml
# configs/experiment_name.yaml

# === Experiment metadata ===
experiment:
  name: "world_model_v2"
  description: "Add latent concept layer to world model"
  date: "2026-05-27"
  base_config: "configs/world_model_v1.yaml"  # parent config

# === Model ===
model:
  architecture: "transformer"
  hidden_dim: 768
  num_layers: 12
  num_heads: 12
  dropout: 0.1
  # ... model-specific params

# === Data ===
data:
  dataset: "my_dataset"
  train_split: "train"
  eval_split: "validation"
  max_length: 512
  batch_size: 32

# === Training ===
training:
  optimizer: "adamw"
  learning_rate: 1e-4
  weight_decay: 0.01
  warmup_steps: 1000
  max_steps: 100000
  scheduler: "cosine"
  gradient_clip: 1.0
  fp16: true
  gradient_accumulation: 4
  seed: 42

# === Evaluation ===
evaluation:
  eval_steps: 1000
  metrics: ["accuracy", "loss", "perplexity"]
  save_best_metric: "accuracy"

# === Logging ===
logging:
  wandb_project: "world-model"
  log_steps: 50
  save_steps: 5000
```

## Config Comparison

When asked to compare two experiment configs:
```
Config A (run_001) vs Config B (run_002):
┌─────────────────────┬─────────────┬─────────────┐
│ Parameter           │ run_001     │ run_002     │
├─────────────────────┼─────────────┼─────────────┤
│ model.hidden_dim    │ 512         │ 768 ✦       │
│ training.lr         │ 1e-4        │ 5e-5 ✦      │
│ training.warmup     │ 500         │ 1000 ✦      │
│ data.batch_size     │ 32          │ 32          │
└─────────────────────┴─────────────┴─────────────┘
✦ = changed

Result: run_002 accuracy 76.2% vs run_001 72.4%
Likely factor: larger model + lower LR with longer warmup
```

## Config Registry (Obsidian)

Save experiment registry to `Research/Experiments/registry.md`:
```markdown
# Experiment Registry

| Run ID | Date | Config | Key Change | Result | Notes |
|--------|------|--------|------------|--------|-------|
| run_001 | 2026-05-20 | v1.yaml | baseline | 72.4% | |
| run_002 | 2026-05-22 | v2.yaml | +hidden_dim | 76.2% | significant gain |
| run_003 | 2026-05-25 | v3.yaml | +concept_layer | 78.1% | best so far |
```

## Tips
- Every experiment should be reproducible from its config + code commit hash
- Use config inheritance (`base_config` field) to avoid duplication
- Always record the git commit hash with each run
- When a run works well, immediately snapshot the config
- Use config groups for related experiments (e.g., all ablation runs)
