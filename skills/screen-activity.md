---
name: screen-activity
description: Query and analyze screen activity captured by the screen monitor daemon
---

# Screen Activity — 屏幕活动查询

查询 Screen Monitor 守护进程采集的屏幕活动数据（截图 + OCR + 窗口信息）。

## 可用操作

### 1. 今日活动摘要
```
screen_today_summary()
```
输出各 App 使用时间、主要活动内容。

### 2. 全文搜索屏幕内容
```
screen_search(query="关键词", date="2026-05-27")
```
搜索 OCR 记录中包含指定关键词的屏幕快照。适合：
- "我今天上午看了哪篇论文？"
- "最近在哪个窗口里看到过 transformer？"
- "我什么时候打开过 Zotero？"

### 3. 活动时间线
```
screen_timeline(date="2026-05-27", hour_start=9, hour_end=18)
```
获取某天的活动切换时间线，按时间顺序展示应用和窗口切换。

## 典型用法

**用户**: "我今天都干了什么？"
1. 调用 `screen_today_summary()` 获取总览
2. 如果需要细节，用 `screen_timeline()` 查看时间线

**用户**: "我昨天在看一篇关于 world model 的论文，叫什么名字来着？"
1. 调用 `screen_search(query="world model", date="昨天日期")`
2. 从 OCR 结果和窗口标题中识别论文名

**用户**: "我这周在 VSCode 里花了多少时间？"
1. 调用 `screen_search(query="", date=None)` 配合 app_name 过滤（通过 timeline 查看）

## 数据位置

- 截图: `~/.cache/pa-screen-monitor/screenshots/YYYY-MM-DD/`
- 数据库: `~/.cache/pa-screen-monitor/ocr.db`
- 保留策略: 截图 7 天，OCR 记录 30 天

## 注意

- Screen Monitor 需要 macOS「屏幕录制」权限
- 数据仅本地存储，OCR 使用 Apple Vision 本地处理
- 守护进程由 launchd 管理 (`com.pa.screen-monitor`)
