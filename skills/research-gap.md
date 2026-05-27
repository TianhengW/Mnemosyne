---
name: research-gap
description: Analyze reading history to find potential research gaps and opportunities
---

# Research Gap Finder

Analyze the user's paper library to identify potential research gaps, under-explored directions, and opportunities for novel contributions.

## Instructions

1. **Map the landscape**: Use `list_collections` to understand the user's research scope, then `get_collection_papers` for key collections (especially "world model", "concept reasoning", "VLM reasoning", "RL")
2. **Identify themes**: Cluster papers by methodology and findings
3. **Check recent trends**: Use `get_daily_papers` or `search_arxiv` to see what's new in the field
4. **Cross-reference**: Look for intersections between the user's collections that have few papers — these might be unexplored areas
5. **Semantic exploration**: Use `semantic_search` with speculative queries like "world model concept abstraction" to see if the user has covered such intersections
6. **Synthesize gaps**: Present actionable research directions

## Analysis Framework

```markdown
## Research Gap Analysis

### Your Coverage Map
- [Topic A]: X papers (strong coverage)
- [Topic B]: Y papers (moderate)
- [Topic C]: Z papers (sparse)

### Identified Gaps

#### Gap 1: [Description]
- **Why it matters:** [relevance to world model / concept reasoning]
- **What exists:** [closest papers you have]
- **What's missing:** [specific angle not covered]
- **Potential direction:** [concrete research idea]

#### Gap 2: ...

### Cross-Domain Opportunities
- [Intersection between your areas that seems under-explored]

### Recommended Next Reads
- [arXiv papers that could fill identified gaps]
```

## Tips for PhD-1 Context
- Focus on gaps that are tractable for a first-year student (not too broad)
- Prioritize gaps between the user's existing strengths (world model + concept reasoning intersection)
- Consider gaps that could lead to a workshop paper or short paper first
- Flag when a gap might already be filled by very recent work (check arXiv)
