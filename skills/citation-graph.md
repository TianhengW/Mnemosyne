---
name: citation-graph
description: Explore paper citation networks and discover unread important papers
---

# Citation Graph — 引用图谱探索

通过 Semantic Scholar API 探索论文的引用网络，发现关键但还没读的论文。

## 可用操作

### 1. 查看引用图谱
```
citation_graph(paper_id="2301.12345", direction="both")
```
- `paper_id`: arXiv ID 或 Semantic Scholar ID
- `direction`: "citations"（被谁引用）、"references"（引用了谁）、"both"
- 自动标记哪些已在 Zotero 中（✅ vs 📋）

### 2. 发现未读高引论文
```
citation_graph_unread(paper_id="2301.12345")
```
从引用网络中找出高引用但你还没读的论文，按引用量排序推荐。

## 典型用法

**用户**: "帮我看看这篇论文的引用网络"
→ `citation_graph(paper_id="2301.12345")`

**用户**: "基于这篇核心论文，我还遗漏了哪些重要工作？"
→ `citation_graph_unread(paper_id="2301.12345")`

**用户**: "谁引用了我最近读的那篇 world model 论文？"
→ 先从 Zotero 搜索获取 arXiv ID → `citation_graph(paper_id, direction="citations")`

## 注意

- Semantic Scholar API 有速率限制，避免短时间大量请求
- arXiv ID 格式：`2301.12345`（无需 `arXiv:` 前缀）
- 与 Zotero 的交叉检查基于标题和 arXiv ID 模糊匹配
