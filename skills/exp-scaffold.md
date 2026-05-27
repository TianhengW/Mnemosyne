---
name: exp-scaffold
description: Generate experiment code scaffold from paper description or method spec
---

# Experiment Scaffold Generator

Generate a clean, runnable experiment code scaffold from a paper description, method specification, or algorithm pseudocode.

## Instructions

1. **Understand the method**: 
   - If a paper key is given, use `get_paper_details` + `get_annotations` to understand the method
   - If a description is given, identify: model architecture, loss function, training procedure, data format

2. **Generate scaffold** following the standard structure below

3. **Fill in key components**:
   - Model definition (PyTorch `nn.Module`)
   - Dataset/DataLoader setup
   - Loss function
   - Training loop with logging
   - Evaluation logic
   - Config management (argparse or YAML)

4. **Provide running instructions**

## Output Structure

```
project_name/
├── configs/
│   └── default.yaml          # Hyperparameters
├── models/
│   └── model.py              # Model architecture
├── data/
│   └── dataset.py            # Dataset + DataLoader
├── train.py                  # Main training script
├── evaluate.py               # Evaluation script
├── utils/
│   ├── logger.py             # Logging utilities
│   └── misc.py               # Helper functions
└── requirements.txt
```

## Code Style Conventions

```python
# Model template
class MyModel(nn.Module):
    def __init__(self, config):
        super().__init__()
        # architecture here

    def forward(self, x, **kwargs):
        # forward pass
        return output

# Training template
def train_one_epoch(model, dataloader, optimizer, config):
    model.train()
    for batch in dataloader:
        loss = compute_loss(model, batch)
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()
```

## Tips
- Always include seed setting for reproducibility
- Add gradient clipping by default
- Include mixed precision (AMP) support
- Add wandb/tensorboard logging hooks (optional flag)
- Include checkpoint saving/loading
- Use `accelerate` or `deepspeed` for multi-GPU if needed
- Default to AdamW optimizer with cosine schedule
