---
name: meeting
description: 会后行动追踪——处理飞书会议纪要、提取 action items、追踪执行进度
---

# Meeting — 会后行动追踪

处理飞书智能纪要，提取 action items，追踪后续执行。

## 使用场景

### 处理新会议纪要
```
/meeting
> [粘贴飞书智能纪要内容]
```

或者指定飞书文档链接：
```
/meeting
> 处理这个会议纪要: https://xxx.feishu.cn/docx/xxxxx
```

### 查看待办进度
```
/meeting
> 我有哪些没完成的 action items？
```

### 准备下次会议前回顾
```
/meeting
> 下次和导师开会需要汇报什么？
```

## Instructions

### 处理会议纪要
1. 如果用户粘贴了文本内容：
   - 调用 `process_meeting_notes(content, title, participants)`
   - 自动提取 action items 和决策
   - 保存到 Obsidian Research/Meetings/

2. 如果用户提供了飞书链接：
   - 调用 `fetch_feishu_doc(doc_url)` 获取内容
   - 然后同上处理

### 追踪 Action Items
1. 调用 `check_action_items("pending")` 查看未完成项
2. 调用 `check_action_items("overdue")` 查看超期项（>7天）
3. 用 `complete_action_item(meeting_filename, item_text)` 标记完成

### 会前准备（配合 /advisor-prep）
1. 调用 `list_meetings()` 查看近期会议
2. 调用 `check_action_items("pending")` 找到上次的承诺
3. 汇总为下次会议的汇报材料

## 飞书集成设置

首次使用需要配置飞书应用：
1. 访问 https://open.feishu.cn/app 创建企业自建应用
2. 添加权限: `docx:document:readonly`
3. 编辑 `config/feishu.json` 填入 app_id 和 app_secret
4. 运行 `uv run scripts/feishu-poll.py --test` 验证

## 自动轮询

配置 launchd 后，每 30 分钟自动检查新会议纪要：
- 发现新纪要 → 自动结构化保存
- 推送微信通知"新会议纪要已整理"

## 与记忆系统的联动

- 会议中的 **决策** → 同步到 Evolving/decisions.md
- 会议中的 **新想法** → 写入 Working/idea-pool.md
- 会议中的 **导师建议** → 更新 Stable/people.md 相关记录
