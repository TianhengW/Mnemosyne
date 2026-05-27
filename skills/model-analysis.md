---
name: model-analysis
description: Analyze model behavior — attention, gradients, features, failure cases
---

# Model Analysis

Tools and techniques for understanding model behavior: attention patterns, gradient flow, feature distributions, and failure mode analysis.

## Analysis Types

### 1. Attention Visualization
```python
import torch
import matplotlib.pyplot as plt
import seaborn as sns

def visualize_attention(model, tokenizer, text, layer=-1, head=0):
    """Visualize attention weights for a given input."""
    inputs = tokenizer(text, return_tensors="pt")
    
    with torch.no_grad():
        outputs = model(**inputs, output_attentions=True)
    
    # attention shape: (batch, heads, seq_len, seq_len)
    attn = outputs.attentions[layer][0, head].cpu().numpy()
    tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
    
    fig, ax = plt.subplots(figsize=(10, 10))
    sns.heatmap(attn, xticklabels=tokens, yticklabels=tokens, ax=ax, cmap="Blues")
    ax.set_title(f"Layer {layer}, Head {head}")
    plt.tight_layout()
    return fig


def attention_entropy(model, inputs):
    """Measure attention entropy (uniformity vs. sparsity)."""
    with torch.no_grad():
        outputs = model(**inputs, output_attentions=True)
    
    entropies = []
    for layer_attn in outputs.attentions:
        # layer_attn: (batch, heads, seq, seq)
        probs = layer_attn + 1e-10
        entropy = -(probs * probs.log()).sum(-1).mean()
        entropies.append(entropy.item())
    return entropies
```

### 2. Gradient Flow Analysis
```python
def plot_gradient_flow(model):
    """Check for vanishing/exploding gradients."""
    layers = []
    avg_grads = []
    max_grads = []
    
    for name, param in model.named_parameters():
        if param.grad is not None and "bias" not in name:
            layers.append(name.replace(".weight", ""))
            avg_grads.append(param.grad.abs().mean().item())
            max_grads.append(param.grad.abs().max().item())
    
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.bar(range(len(layers)), max_grads, alpha=0.5, label="max gradient")
    ax.bar(range(len(layers)), avg_grads, alpha=0.8, label="mean gradient")
    ax.set_xticks(range(len(layers)))
    ax.set_xticklabels(layers, rotation=90, fontsize=6)
    ax.set_ylabel("Gradient magnitude")
    ax.set_yscale("log")
    ax.legend()
    plt.tight_layout()
    return fig
```

### 3. Feature Distribution Analysis
```python
def analyze_hidden_states(model, dataloader, num_batches=10):
    """Analyze hidden state statistics across layers."""
    model.eval()
    layer_stats = {}
    
    with torch.no_grad():
        for i, batch in enumerate(dataloader):
            if i >= num_batches:
                break
            outputs = model(**batch, output_hidden_states=True)
            
            for layer_idx, hidden in enumerate(outputs.hidden_states):
                if layer_idx not in layer_stats:
                    layer_stats[layer_idx] = {"mean": [], "std": [], "dead_frac": []}
                
                layer_stats[layer_idx]["mean"].append(hidden.mean().item())
                layer_stats[layer_idx]["std"].append(hidden.std().item())
                dead_frac = (hidden.abs() < 1e-6).float().mean().item()
                layer_stats[layer_idx]["dead_frac"].append(dead_frac)
    
    return layer_stats
```

### 4. Failure Case Analysis
```python
def find_failure_cases(model, eval_dataset, tokenizer, n=20):
    """Find the worst predictions for qualitative analysis."""
    model.eval()
    failures = []
    
    for item in eval_dataset:
        inputs = tokenizer(item["input"], return_tensors="pt").to(model.device)
        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=128)
        
        prediction = tokenizer.decode(output[0], skip_special_tokens=True)
        
        # Compute error metric
        score = compute_metric(prediction, item["target"])
        failures.append({
            "input": item["input"],
            "target": item["target"],
            "prediction": prediction,
            "score": score,
        })
    
    # Sort by worst performance
    failures.sort(key=lambda x: x["score"])
    return failures[:n]
```

### 5. Representation Similarity (CKA/SVCCA)
```python
def centered_kernel_alignment(X, Y):
    """Compute CKA between two sets of representations."""
    def centering(K):
        n = K.shape[0]
        H = torch.eye(n) - torch.ones(n, n) / n
        return H @ K @ H
    
    K_X = centering(X @ X.T)
    K_Y = centering(Y @ Y.T)
    
    hsic_xy = (K_X * K_Y).sum()
    hsic_xx = (K_X * K_X).sum()
    hsic_yy = (K_Y * K_Y).sum()
    
    return hsic_xy / (hsic_xx.sqrt() * hsic_yy.sqrt())
```

### 6. Probing / Linear Evaluation
```python
def train_probe(model, dataset, target_property, layer=-1):
    """Train a linear probe to test what information is encoded."""
    model.eval()
    features = []
    labels = []
    
    with torch.no_grad():
        for item in dataset:
            inputs = tokenizer(item["text"], return_tensors="pt").to(model.device)
            outputs = model(**inputs, output_hidden_states=True)
            hidden = outputs.hidden_states[layer][:, -1, :]  # last token
            features.append(hidden.cpu())
            labels.append(item[target_property])
    
    X = torch.cat(features)
    y = torch.tensor(labels)
    
    # Train linear probe
    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression(max_iter=1000)
    clf.fit(X.numpy(), y.numpy())
    return clf.score(X.numpy(), y.numpy())
```

## When to Use Each Analysis

| Symptom | Analysis to Run |
|---------|----------------|
| Model ignoring certain inputs | Attention visualization |
| Training stuck | Gradient flow |
| Unexpected predictions | Failure case analysis |
| "Does my model learn X?" | Probing |
| Comparing two model versions | CKA / representation similarity |
| Dead neurons / collapse | Feature distribution |
| Performance drop on specific subset | Stratified error analysis |
