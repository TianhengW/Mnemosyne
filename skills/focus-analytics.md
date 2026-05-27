---
name: focus-analytics
description: Analyze focus patterns and productivity from screen monitor data
---

# Focus Analytics — 专注度分析

基于 Screen Monitor 采集的数据分析专注模式和工作效率。

## 可用操作

### 1. 每日专注分析
```
focus_analytics(date="2026-05-27")
```
输出：
- 深度工作时段（连续 10+ 分钟不切换 App）
- App 切换频率和专注评级（A-D）
- 分心应用识别
- 每小时切换热力图
- 最高效时段推荐

### 2. 周趋势
```
focus_weekly_trend()
```
显示过去 7 天每日的活跃时间、深度工作时长、切换次数和评级。

## 专注评级标准

| 评级 | 切换频率 | 含义 |
|------|----------|------|
| A 🟢 | < 5/h | 极度专注（心流状态） |
| B 🟡 | 5-10/h | 良好 |
| C 🟠 | 10-20/h | 一般（可改善） |
| D 🔴 | > 20/h | 频繁切换（需关注） |

## 典型用法

**用户**: "我今天专注度怎么样？"
→ `focus_analytics()`

**用户**: "这周我的工作效率趋势如何？"
→ `focus_weekly_trend()`

**用户**: "什么时间段我最高效？"
→ `focus_analytics()` → 看"最高效时段"部分
