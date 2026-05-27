---
name: train-debug
description: Systematically diagnose and fix training issues
---

# Training Debugger

Systematic diagnosis of common deep learning training issues with actionable fixes.

## Diagnostic Flow

When the user reports a training problem, follow this decision tree:

### 1. Loss Issues

**Loss is NaN/Inf:**
- Check learning rate (too high?)
- Check for division by zero in loss
- Check input data for NaN/Inf values
- Add gradient clipping: `torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)`
- Try lower precision stability: `torch.autograd.detect_anomaly()`
- Check if softmax input is too large → use log_softmax

**Loss not decreasing:**
- Verify data loading is correct (visualize a batch)
- Check if model is in train mode: `model.train()`
- Verify gradient flow: `for name, p in model.named_parameters(): print(name, p.grad.norm())`
- Try 10x smaller learning rate
- Overfit on single batch first to verify model capacity
- Check label alignment with data

**Loss explodes after N steps:**
- Learning rate too high for this phase → use warmup
- Gradient accumulation causing effective LR to be too high
- Data distribution shift (check batch statistics)
- Numerical instability in specific layer

### 2. Memory Issues

**CUDA OOM:**
```python
# Quick fixes (in order of preference):
# 1. Reduce batch size
# 2. Enable gradient checkpointing
model.gradient_checkpointing_enable()
# 3. Use mixed precision
scaler = torch.cuda.amp.GradScaler()
with torch.cuda.amp.autocast():
    loss = model(batch)
# 4. Gradient accumulation (simulate larger batch)
# 5. Move to model parallelism / DeepSpeed ZeRO
```

**Memory leak:**
```python
# Common causes:
# 1. Storing tensors in list without detach
losses.append(loss.detach().item())  # NOT loss
# 2. Not clearing cache
torch.cuda.empty_cache()
# 3. Tensorboard/wandb logging tensors
writer.add_scalar('loss', loss.item(), step)  # .item() is key
```

### 3. Convergence Issues

**Model underfitting:**
- Increase model capacity (layers, hidden dim)
- Train longer
- Check data quality
- Reduce regularization (dropout, weight decay)

**Model overfitting:**
- Add data augmentation
- Increase dropout
- Add weight decay
- Early stopping
- More training data

**Training unstable (oscillating loss):**
- Reduce learning rate
- Increase batch size
- Add gradient clipping
- Use learning rate warmup
- Check for data issues (mislabeled, duplicates)

### 4. Speed Issues

**Training too slow:**
```python
# Checklist:
# 1. DataLoader workers
DataLoader(..., num_workers=4, pin_memory=True, prefetch_factor=2)
# 2. Mixed precision training
# 3. Compile model (PyTorch 2.0+)
model = torch.compile(model)
# 4. Profile to find bottleneck
torch.profiler.profile(activities=[...])
# 5. Check GPU utilization
# nvidia-smi or torch.cuda.utilization()
```

### 5. Distributed Training Issues

**Multi-GPU not scaling:**
- Check communication overhead (NCCL)
- Ensure batch size scales with GPU count
- Verify all GPUs are utilized: `nvidia-smi -l 1`
- Check for synchronization bottlenecks

## Quick Diagnostic Script

```python
def diagnose_training(model, dataloader, optimizer):
    """Run basic diagnostics before full training."""
    model.train()
    batch = next(iter(dataloader))
    
    # Test forward pass
    with torch.no_grad():
        output = model(batch)
        print(f"Output range: [{output.min():.4f}, {output.max():.4f}]")
    
    # Test backward pass
    loss = compute_loss(model, batch)
    loss.backward()
    
    # Check gradients
    total_norm = 0
    for p in model.parameters():
        if p.grad is not None:
            total_norm += p.grad.norm().item() ** 2
    total_norm = total_norm ** 0.5
    print(f"Gradient norm: {total_norm:.4f}")
    
    # Check for dead neurons
    for name, p in model.named_parameters():
        if p.grad is not None and p.grad.norm() == 0:
            print(f"WARNING: Zero gradient for {name}")
    
    # Overfit single batch test
    for i in range(100):
        optimizer.zero_grad()
        loss = compute_loss(model, batch)
        loss.backward()
        optimizer.step()
        if i % 20 == 0:
            print(f"Step {i}: loss={loss.item():.4f}")
```
