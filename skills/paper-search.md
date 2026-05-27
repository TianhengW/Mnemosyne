---
name: paper-search
description: Search and browse papers in Zotero library
---

# Paper Search

Search the user's Zotero library for papers related to a topic, author, or keyword.

## Instructions

1. Use the `search_papers` MCP tool from the `zotero` server to find papers matching the user's query
2. Present results in a clean, scannable format
3. If the user wants details on a specific paper, use `get_paper_details` to get full metadata
4. If the user wants to see their annotations, use `get_annotations`
5. Offer to check which collection the paper belongs to for context on the user's research organization

## Example Usage

User: "Find papers about reinforcement learning for reasoning"
→ Call `search_papers` with query "reinforcement learning reasoning"
→ Present top results with title, authors, date
→ Ask if they want details or annotations on any specific paper

User: "What did I highlight in the DeepSeek paper?"
→ Search for "DeepSeek" → get paper key → call `get_annotations`
