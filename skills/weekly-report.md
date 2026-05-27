---
name: weekly-report
description: Generate weekly research progress report for advisor
---

# Weekly Research Report Generator

Automatically generate a weekly progress report based on recently read papers, notes, and research activities.

## Instructions

1. **Gather this week's activities:**
   - `get_recent_papers(days=7)` — papers added this week
   - `list_notes(folder="Daily")` — daily notes from this week
   - `search_notes(query="")` with date filtering — any notes modified recently

2. **For each new paper**, get brief details via `get_paper_details` to understand what was read

3. **Check annotations**: For papers with annotations, use `get_annotations` to extract key takeaways

4. **Check Obsidian**: Look for research notes created this week

5. **Generate the report** following the template below

## Report Template

```markdown
# 周报 [YYYY-MM-DD]

## 本周阅读
| 论文 | 方向 | 关键收获 |
|------|------|----------|
| [Title] (Author, Year) | [topic] | [1-sentence takeaway] |

## 研究进展
- [What was accomplished this week]
- [Key insights or breakthroughs]

## 遇到的问题
- [Challenges or blockers]

## 下周计划
- [Based on reading trajectory and open questions]

## 想法/灵感
- [Any new ideas sparked by this week's reading]
```

## Notes
- Tailor the tone for sharing with an advisor (concise, focused on progress)
- Highlight connections between papers read and the user's research direction (world model, concept reasoning)
- If very few papers were read, focus more on research progress and ideas
- Save the report to Obsidian at `Daily/周报-YYYY-MM-DD.md`
