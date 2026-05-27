---
name: explain-paper
description: Deep-dive explanation of a paper's method, math, and contribution
---

# Paper Explainer

Provide deep, pedagogical explanations of papers — including methods, math, and intuitions.

## Instructions

1. Get the paper's details and annotations from Zotero
2. Based on the user's question, provide explanation at the right level:
   - **Overview**: Big picture of what the paper does and why
   - **Method**: Step-by-step walkthrough of the approach
   - **Math**: Formula-by-formula explanation with intuitions
   - **Comparison**: How it differs from related methods

## Explanation Approach

### For methods/algorithms:
```
1. What problem is being solved? (input/output)
2. What's the key insight? (one sentence intuition)
3. Walk through the pipeline step by step
4. For each step: what does it do, why is it needed, what are alternatives
5. What makes this different from prior work?
```

### For math/formulas:
```
1. State what the formula computes (in plain language)
2. Define every symbol
3. Break into sub-expressions and explain each
4. Give intuition: "when X is large, this term dominates because..."
5. Connect to the bigger picture: "this ensures that..."
```

### For concepts:
```
1. Define the concept simply
2. Give an analogy or example
3. Explain why it matters in this context
4. Connect to things the user already knows (check their library)
```

## Example Prompts
- "Explain the GRPO algorithm step by step"
- "What does the objective function in this paper actually optimize?"
- "Help me understand the world model architecture in [paper]"
- "What's the difference between DPO and GRPO mathematically?"
- "I don't understand equation 3 in [paper], break it down"

## Tips
- Always connect to the user's research context (world model, concept reasoning)
- Use the user's own annotations to understand what they found confusing
- If the user has annotated a formula with "?", that's a clear signal they need help
- Suggest related papers from their library that might help build intuition
