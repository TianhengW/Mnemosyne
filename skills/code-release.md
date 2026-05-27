---
name: code-release
description: Prepare research code for open-source release
---

# Code Release Preparation

Prepare research code for public release alongside a paper publication.

## Instructions

When the user wants to release their code:
1. Audit the codebase for release readiness
2. Generate necessary files (README, LICENSE, setup)
3. Clean up code and add minimal documentation
4. Create reproducibility checklist

## Release Checklist

### Must Have
- [ ] `README.md` with: title, abstract, installation, usage, citation
- [ ] `requirements.txt` or `environment.yaml` with pinned versions
- [ ] `LICENSE` (MIT or Apache-2.0 for maximum adoption)
- [ ] Working training script with default config that reproduces paper results
- [ ] Pre-trained model checkpoints (HuggingFace Hub or Google Drive)
- [ ] Clear instructions to reproduce main table

### Should Have
- [ ] `scripts/` directory with shell scripts for key experiments
- [ ] Example inference/demo script
- [ ] Docker/Singularity file for exact environment
- [ ] Config files matching paper experiments
- [ ] Evaluation script with expected output

### Nice to Have
- [ ] Gradio/Streamlit demo
- [ ] Colab notebook
- [ ] Pre-computed results for verification
- [ ] Visualization scripts for paper figures
- [ ] Unit tests for core components

## README Template

```markdown
# [Paper Title]

[![Paper](https://img.shields.io/badge/Paper-arXiv-red)](https://arxiv.org/abs/XXXX.XXXXX)
[![Model](https://img.shields.io/badge/Model-HuggingFace-yellow)](https://huggingface.co/xxx)

Official implementation of "[Paper Title]" (Venue Year).

## Abstract
[One paragraph abstract]

## Installation
\```bash
conda create -n mymethod python=3.10
conda activate mymethod
pip install -r requirements.txt
\```

## Quick Start
\```python
from mymethod import Model
model = Model.from_pretrained("xxx/model-name")
result = model.predict(input)
\```

## Training
\```bash
# Reproduce Table 1 main results
bash scripts/train_main.sh

# Run ablation (Table 2)
bash scripts/run_ablation.sh
\```

## Model Zoo
| Model | Dataset | Metric | Checkpoint |
|-------|---------|--------|------------|
| Ours-Base | Dataset1 | 78.6% | [link]() |
| Ours-Large | Dataset1 | 82.3% | [link]() |

## Citation
\```bibtex
@inproceedings{author2026method,
  title={Paper Title},
  author={Author1 and Author2},
  booktitle={Venue},
  year={2026}
}
\```

## Acknowledgments
[Funding, compute resources, based-on code]
```

## Code Cleanup Guidelines
- Remove all hardcoded paths (use argparse/config)
- Remove debug prints and commented-out code
- Remove personal API keys or credentials
- Remove experiment-specific hacks that aren't part of the method
- Ensure all imports are used
- Add type hints to public functions
- One-line docstrings for non-obvious functions
