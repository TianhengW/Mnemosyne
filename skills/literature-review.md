---
name: literature-review
description: Conduct a literature review on a research topic using Zotero library
---

# Literature Review

Conduct a structured literature review on a research topic by pulling relevant papers, annotations, and notes from the user's knowledge base.

## Instructions

1. **Identify scope**: Understand the research topic or question
2. **Search collections**: Use `list_collections` to find relevant collections, then `get_collection_papers` to get papers in those collections
3. **Search by keyword**: Use `search_papers` for broader keyword searches
4. **Gather annotations**: For key papers, use `get_annotations` to see what the user highlighted and noted
5. **Check notes**: Use `search_notes` from the `obsidian` server to find any related research notes
6. **Synthesize**: Organize findings into themes, summarize key contributions, and identify gaps

## Output Format

```markdown
## Literature Review: [Topic]

### Key Themes
- Theme 1: [papers]
- Theme 2: [papers]

### Paper Summaries
1. **[Title]** (Author, Year)
   - Main contribution: ...
   - User's notes: ...

### Research Gaps
- ...

### Suggested Next Steps
- ...
```

## Tips
- Focus on papers the user has annotated — these are likely more relevant to their current work
- Cross-reference with Obsidian notes to understand the user's perspective
- Group papers by methodology, findings, or chronology as appropriate
