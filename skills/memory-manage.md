---
name: memory-manage
description: Manage the layered memory system — consolidate, promote, decay, recall
---

# Memory Manager — 记忆管理

管理分层记忆系统的核心机制：写入、整合、晋升、衰减、检索。

## 记忆金字塔

```
┌──────────────────────────────────────────────────┐
│  Core (恒久)                                      │
│  性格、世界观、认知风格                              │
│  文件: Digital-Self/Core/                          │
│  更新: 极少（重大人生转变时）                         │
├──────────────────────────────────────────────────┤
│  Stable (年级)                                    │
│  研究品味、方法论偏好、长期目标、人际关系              │
│  文件: Digital-Self/Stable/                        │
│  更新: 每几个月                                    │
├──────────────────────────────────────────────────┤
│  Evolving (月级)                                  │
│  领域认知、技能水平、决策日志                         │
│  文件: Digital-Self/Evolving/                      │
│  更新: 读完重要论文/完成项目/做重大决策后              │
├──────────────────────────────────────────────────┤
│  Working (周级)                                   │
│  当前阅读、活跃想法、近期洞察、本周目标               │
│  文件: Digital-Self/Working/                       │
│  更新: 每次对话中，每周整理                          │
├──────────────────────────────────────────────────┤
│  Ephemeral (日级)                                 │
│  今日待办、临时笔记、草稿                            │
│  文件: Digital-Self/Ephemeral/                     │
│  更新: 每日，7天后自动清理                           │
└──────────────────────────────────────────────────┘
```

## 核心操作

### 1. 写入（Write）
对话中出现新信息时，判断该存入哪一层：

| 信息类型 | 存入层 | 示例 |
|----------|--------|------|
| 性格/价值观表达 | Core | "我是那种一定要搞清楚why的人" |
| 研究品味/偏好 | Stable | "我更看重idea的优雅而不是性能的绝对值" |
| 对某方向的新认知 | Evolving | "读完X论文后我意识到Y方向的关键在于Z" |
| 本周在做的事 | Working | "这周在看world model的几篇新论文" |
| 临时想法 | Ephemeral | "明天要试一下把X改成Y看看效果" |

### 2. 晋升（Promote）
低层记忆经过验证/沉淀后，向上晋升：

```
Ephemeral → Working: 临时想法值得继续思考
Working → Evolving: 
  - 某个洞察被反复引用
  - 某个想法已成型为研究方向
  - 技能有了实质性提升
Evolving → Stable: 
  - 某个认知已经稳定不再变化
  - 某个偏好被多次验证
Stable → Core: 
  - 几乎不发生，除非重大人生观改变
```

**晋升触发时机**:
- `/weekly-report` 时：Working → Evolving
- `/monthly-review` 时：Evolving → Stable
- 用户明确说"这是我确定的看法"时

### 3. 衰减（Decay）
低层记忆如果不被引用，逐渐失去活跃性：

| 层 | 衰减规则 |
|----|----------|
| Ephemeral | 7天未更新 → 自动清理 |
| Working | 4周未引用 → 标记为"待整理"，下次 weekly-report 时决定晋升或删除 |
| Evolving | 不主动衰减，但每季度 review 时检查是否过时 |
| Stable/Core | 不衰减 |

### 4. 整合（Consolidate）
定期将碎片整合为结构化知识：

**每周整合（`/weekly-report` 触发）：**
1. 读取 Working/current-context.md
2. 将本周洞察中 ⭐⭐⭐ 的晋升到 Evolving/domain-knowledge.md
3. 清理已完成/过时的 Working 内容
4. 更新 Working 中的"本周目标"

**每月整合（手动触发 `/memory-manage`）：**
1. 回顾 Evolving 层所有"最近的认知更新"
2. 检查是否有稳定的新认知可以晋升到 Stable
3. 检查 Stable 层是否有过时内容需要修正
4. 整理 Working/idea-pool.md，成型的转入 Research/Ideas/

### 5. 检索（Recall）
被问到某个话题时的检索策略：

```
1. 先查 Core（看用户的思维偏好、价值观是否相关）
2. 查 Stable（研究品味、方法论偏好）
3. 查 Evolving（对该方向的当前认知）
4. 查 Working（最近是否在想这个问题）
5. 如果都没有 → 说明这是新话题，正常讨论，讨论后写入 Working
```

## 对话中的自动行为

每次对话中，Claude 应该：
- 检测到**新洞察**时 → 写入 Working/current-context.md 的"近期洞察"
- 检测到**决策**时 → 写入 Evolving/decisions.md
- 检测到**观点变化**时 → 更新对应层的文件，并记录变化原因
- 检测到**新想法**时 → 写入 Working/idea-pool.md
- 检测到**性格/价值观表达**时 → 确认后写入 Core

## 完整性承诺

> 你的每一个重要想法都不会丢失。
> 它们要么在 Working 中等待发酵，
> 要么已经晋升到更高层成为你知识体系的一部分，
> 要么被有意识地放弃并记录了原因。
> 没有东西会悄悄消失——要么在金字塔中，要么在 Killed Ideas 里。
