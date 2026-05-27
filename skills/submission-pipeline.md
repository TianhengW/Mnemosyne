---
name: submission-pipeline
description: Manage paper submission workflow from idea to publication
---

# Submission Pipeline — 投稿管线

管理论文从 idea 到发表的完整流程。

## 可用操作

### 1. 创建投稿项目
```
create_submission(paper_title="...", target_venue="NeurIPS 2026", deadline="2026-05-22", stage="idea")
```
阶段: idea → outline → draft → internal_review → submit → camera_ready → published

### 2. 更新进度
```
update_submission(paper_title="...", stage="draft", note="初稿完成第3节")
```

### 3. 总览仪表盘
```
submission_dashboard()
```
显示所有投稿项目的阶段、deadline、剩余时间。

## Pipeline 阶段

| 阶段 | 含义 | 建议动作 |
|------|------|----------|
| 💡 idea | 确定研究问题 | 文献调研、可行性分析 |
| 📋 outline | 论文大纲 | 明确实验计划、分工 |
| 📝 draft | 撰写初稿 | 每日写作追踪 |
| 🔍 internal_review | 内部审阅 | 导师/同学反馈 |
| 📤 submit | 投稿 | 格式检查、匿名化 |
| 📐 camera_ready | 终稿 | 修改 + 最终版 |
| 🎉 published | 已发表 | 🎉 |

## 典型用法

**用户**: "我想投 NeurIPS，帮我建个投稿管线"
→ `create_submission(paper_title="...", target_venue="NeurIPS 2026", deadline="2026-05-22")`

**用户**: "看看我现在有哪些在投的论文"
→ `submission_dashboard()`

## 数据位置

投稿记录存储在: `Obsidian Vault/Research/Submissions/`
