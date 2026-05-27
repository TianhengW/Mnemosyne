---
name: repo-init
description: Initialize a standardized ML research project structure
---

# Research Project Initializer

Create a clean, standardized project structure for ML research that's reproducible and publication-ready from day one.

## Instructions

When starting a new research project:
1. Ask for project name and brief description
2. Generate the full directory structure
3. Include boilerplate configs, training loop, and utils
4. Set up git with appropriate .gitignore

## Standard Structure

```
project_name/
├── configs/
│   ├── default.yaml           # Base config
│   └── experiment/            # Per-experiment overrides
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── model.py           # Main model
│   ├── data/
│   │   ├── __init__.py
│   │   └── dataset.py         # Dataset + transforms
│   ├── losses/
│   │   ├── __init__.py
│   │   └── loss.py            # Loss functions
│   └── utils/
│       ├── __init__.py
│       ├── logger.py          # W&B/TB logging
│       ├── metrics.py         # Evaluation metrics
│       └── misc.py            # Seed, distributed, etc.
├── scripts/
│   ├── train.sh               # Training launch script
│   ├── eval.sh                # Evaluation script
│   └── sweep.sh               # Hyperparameter sweep
├── tools/
│   ├── train.py               # Main training entry
│   ├── evaluate.py            # Evaluation entry
│   └── visualize.py           # Visualization tools
├── outputs/                   # Experiment outputs (gitignored)
├── data/                      # Data directory (gitignored)
├── tests/
│   └── test_model.py          # Basic sanity tests
├── .gitignore
├── requirements.txt
├── setup.py                   # or pyproject.toml
└── README.md
```

## Key Boilerplate Files

### .gitignore
```
outputs/
data/
*.pyc
__pycache__/
*.egg-info/
.eggs/
dist/
build/
wandb/
*.pt
*.pth
*.ckpt
.DS_Store
*.log
```

### default.yaml
```yaml
seed: 42
project_name: "my_project"

model:
  name: "my_model"
  # architecture params

data:
  dataset: "dataset_name"
  train_path: "data/train"
  val_path: "data/val"
  batch_size: 32
  num_workers: 4

training:
  epochs: 100
  lr: 1e-4
  optimizer: "adamw"
  weight_decay: 0.01
  scheduler: "cosine"
  warmup_steps: 1000
  grad_clip: 1.0
  fp16: true
  
evaluation:
  eval_every: 1000
  metrics: ["accuracy"]

logging:
  wandb: true
  log_every: 50
  save_every: 5000
```

### train.py skeleton
```python
import argparse
import yaml
import torch
from pathlib import Path

from src.models import build_model
from src.data import build_dataloader
from src.utils.misc import set_seed, setup_distributed
from src.utils.logger import setup_logger


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--output_dir", type=str, default="outputs/default")
    parser.add_argument("--resume", type=str, default=None)
    parser.add_argument("opts", nargs=argparse.REMAINDER)  # Override any config
    return parser.parse_args()


def main():
    args = parse_args()
    config = yaml.safe_load(open(args.config))
    
    set_seed(config["seed"])
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    logger = setup_logger(config, args.output_dir)
    
    model = build_model(config["model"])
    train_loader = build_dataloader(config["data"], split="train")
    val_loader = build_dataloader(config["data"], split="val")
    
    optimizer = torch.optim.AdamW(model.parameters(), lr=config["training"]["lr"])
    
    # Training loop
    for epoch in range(config["training"]["epochs"]):
        train_one_epoch(model, train_loader, optimizer, logger, config)
        if (epoch + 1) % config["evaluation"]["eval_every"] == 0:
            evaluate(model, val_loader, logger)
            save_checkpoint(model, optimizer, epoch, args.output_dir)


if __name__ == "__main__":
    main()
```

## Variant Structures

### For HuggingFace-based projects
Replace `src/models/` with direct use of `transformers`, add `src/trainers/` for custom Trainer subclass.

### For RL projects
Add `src/envs/`, `src/agents/`, `src/buffers/`.

### For generation projects  
Add `src/samplers/`, `src/metrics/fid.py`, `src/visualization/`.
