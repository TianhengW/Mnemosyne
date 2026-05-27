---
name: paper-compare
description: Generate comparison tables across multiple papers
---

# Paper Comparison Table Generator

Generate structured comparison tables for a set of papers. Useful for Related Work sections, survey writing, and understanding the landscape.

## Instructions

1. **Get paper details**: For each paper key provided, call `get_paper_details` to get metadata and `get_annotations` for user notes
2. **Identify dimensions**: Based on the papers, determine comparison axes:
   - Method/Approach
   - Dataset/Benchmark
   - Key Results/Metrics
   - Contribution/Novelty
   - Limitations
3. **Generate the table** in markdown format
4. **Optionally save** to Obsidian if requested

## Output Format

```markdown
## Comparison: [Topic]

| Paper | Method | Dataset | Key Metric | Contribution |
|-------|--------|---------|------------|--------------|
| Author (Year) | ... | ... | ... | ... |

### Detailed Analysis

#### [Paper 1 Title]
- **Approach:** ...
- **Strengths:** ...
- **Limitations:** ...
- **Relation to our work:** ...

#### [Paper 2 Title]
...

### Summary of Trends
- [What patterns emerge across these papers]
- [Where is the field heading]
- [Opportunity for differentiation]
```

## Usage Examples

- "Compare these 5 RL reasoning papers: [keys]"
- "Make a comparison table of world model approaches I've read"
- "Compare the methods in my 'concept reasoning' collection"

## Tips
- When comparing papers from a collection, first use `get_collection_papers` to get all keys
- Focus on dimensions most relevant to the user's research direction
- Highlight where each paper stands relative to the user's planned approach
- Use the user's own annotations to inform the "relation to our work" section
