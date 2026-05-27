---
name: research-note
description: Generate structured research notes and save to Obsidian
---

# Research Note

Generate a structured research note for a paper and save it to the Obsidian vault.

## Instructions

1. Get the paper's details using `get_paper_details` from the `zotero` server
2. Get the user's annotations using `get_annotations`
3. Generate a structured note following the template below
4. Save to Obsidian using `create_note` in the `Papers/` folder
5. Use the paper's title (cleaned) as the filename

## Note Template

```markdown
# [Paper Title]

## Metadata
- **Authors:** [authors]
- **Year:** [year]
- **Venue:** [journal/conference]
- **DOI:** [doi]
- **Zotero Key:** [key]
- **Collections:** [collections]

## Summary
[2-3 sentence summary of the paper's main contribution]

## Key Ideas
- [bullet points of core ideas]

## Methodology
- [approach/method used]

## My Annotations
[User's highlights and comments from Zotero, organized by theme]

## Connections
- [[related paper 1]]
- [[related paper 2]]

## Questions & Thoughts
- [open questions or ideas sparked by this paper]
```

## Naming Convention
- File path: `Papers/[First Author] [Year] - [Short Title].md`
- Example: `Papers/Wang 2024 - DeepSeekMath.md`
