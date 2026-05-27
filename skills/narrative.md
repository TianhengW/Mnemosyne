---
name: narrative
description: Build research narrative timelines from experiments, decisions, papers, and ideas
---

# Research Narrative — 研究叙事构建

从多个数据源聚合研究时间线，帮助用户回顾研究历程、梳理思路演变、准备开题/中期报告。

## 可用操作

### 1. 构建主题叙事
```
build_narrative(topic="world model", start_date="2026-01-01", end_date="2026-05-27")
```
为指定研究主题构建叙事时间线，聚合：
- Zotero 中相关论文的阅读时间和批注
- Obsidian 中的决策日志 (`Evolving/decisions.md`)
- 实验记录 (`Research/Experiments/`)
- 跨论文连接 (`Research/Connections/`)
- 想法池演变 (`Working/idea-pool.md`)

### 2. 研究活动总时间线
```
research_timeline(months=6)
```
生成最近 N 个月的研究活动总时间线（不限定主题）。

## 输出格式

叙事按月组织，每月包含：
- 阅读了哪些关键论文
- 产生了什么想法和洞察
- 做了什么决策
- 跑了什么实验
- 当前状态总结

## 典型用法

**用户**: "帮我梳理一下我对 world model 的研究历程"
→ `build_narrative(topic="world model", start_date="2025-09-01", end_date="2026-05-27")`

**用户**: "我需要准备开题报告，帮我回顾这半年的研究轨迹"
→ `research_timeline(months=6)`

**用户**: "从什么时候开始我对 concept reasoning 感兴趣的？"
→ `build_narrative(topic="concept reasoning", start_date="2025-01-01", end_date="2026-05-27")`

## 数据源

| 来源 | 路径 | 信息 |
|------|------|------|
| Zotero | MCP `search_papers` | 论文阅读时间线 |
| Obsidian | `Digital-Self/Evolving/decisions.md` | 决策节点 |
| Obsidian | `Research/Experiments/` | 实验记录 |
| Obsidian | `Research/Connections/` | 跨论文连接 |
| Obsidian | `Digital-Self/Working/idea-pool.md` | 想法演变 |
| Obsidian | `Digital-Self/Evolving/domain-knowledge.md` | 领域认知 |

## 注意

- 叙事质量依赖于日常记录的完整性
- 如果某时期记录缺失，叙事中会标注"数据空白"
- 建议配合 `/memory-manage` 定期整理记忆层，丰富叙事素材
