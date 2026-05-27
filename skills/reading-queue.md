---
name: reading-queue
description: Manage paper reading queue with priorities
---

# Reading Queue Manager

Manage a prioritized reading queue to stay organized during the paper accumulation phase of PhD research.

## Instructions

### Adding papers to the queue:
1. When the user says "add to reading list" or "I should read this", add it
2. Use `search_arxiv` or `search_papers` to get paper details
3. Assign priority based on relevance to research direction
4. Save/update the queue at `Research/reading-queue.md`

### Reviewing the queue:
1. Read `Research/reading-queue.md`
2. Show the current queue organized by priority
3. Suggest which to read next based on:
   - Priority level
   - Relevance to current focus
   - Whether it's a prerequisite for other queued papers

### After reading:
1. Move from "To Read" to "Read" section
2. Suggest creating a research note (`/research-note`)

## Queue Format

```markdown
# Reading Queue

Last updated: YYYY-MM-DD

## 🔴 High Priority (read this week)
- [ ] [Paper Title](arxiv_link) — [why it's relevant]
- [ ] [Paper Title](arxiv_link) — [why it's relevant]

## 🟡 Medium Priority (read this month)
- [ ] [Paper Title](arxiv_link) — [reason]

## 🟢 Low Priority (when time allows)
- [ ] [Paper Title](arxiv_link) — [reason]

## ✅ Recently Read
- [x] [Paper Title] — [date read] — [one-line takeaway]
```

## Priority Criteria
- **High**: Directly related to current research, cited by advisor, needed for ongoing work
- **Medium**: Related to research direction, highly cited, recommended by peers
- **Low**: Interesting but tangential, good for broadening perspective

## Tips
- Keep the queue manageable (max ~15 active items)
- Re-prioritize weekly during `/weekly-report`
- Use HuggingFace daily papers to discover new candidates
- Cross-reference with `semantic_search` to check if similar papers were already read
