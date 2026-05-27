---
name: notify
description: 管理微信推送通知——发送消息、配置推送、管理定时任务
---

# Notify — 微信推送管理

管理通过 Server酱 向微信推送通知的功能。

## 可用操作

### 快速推送
- `send_wechat(title, content)` — 立即发送一条消息到微信
- `push_daily_papers()` — 聚合今日新论文并推送
- `push_deadline_alert()` — 推送临近的 deadline 提醒
- `push_work_summary(summary)` — 推送工作完成通知

### 配置管理
- `get_push_config()` — 查看当前推送配置
- `update_push_config(key, value)` — 修改推送设置

## 首次设置

1. 访问 https://sct.ftqq.com/ 注册并获取 SendKey
2. 配置 SendKey:
   ```
   调用 update_push_config("serverchan_sendkey", "你的SendKey")
   ```
3. 发送测试:
   ```
   调用 send_wechat("测试", "Hello from PA!")
   ```

## 定时推送管理

定时推送由 macOS launchd 管理，独立于 Claude Code 运行。

### 启用定时推送
```bash
# 链接 plist 到 LaunchAgents
ln -sf ~/Documents/Autolab/codes/PA/launchd/com.pa.daily-push.morning.plist ~/Library/LaunchAgents/
ln -sf ~/Documents/Autolab/codes/PA/launchd/com.pa.daily-push.evening.plist ~/Library/LaunchAgents/

# 加载定时任务
launchctl load ~/Library/LaunchAgents/com.pa.daily-push.morning.plist
launchctl load ~/Library/LaunchAgents/com.pa.daily-push.evening.plist
```

### 禁用定时推送
```bash
launchctl unload ~/Library/LaunchAgents/com.pa.daily-push.morning.plist
launchctl unload ~/Library/LaunchAgents/com.pa.daily-push.evening.plist
```

### 手动测试
```bash
uv run ~/Documents/Autolab/codes/PA/scripts/daily-push.py --type test
uv run ~/Documents/Autolab/codes/PA/scripts/daily-push.py --type morning
uv run ~/Documents/Autolab/codes/PA/scripts/daily-push.py --type evening
```

## 推送时间表

| 时间 | 内容 | 类型 |
|------|------|------|
| 08:30 | 今日论文推荐 + Deadline 提醒 | 早间推送 |
| 21:00 | 今日代码活动 + 本周目标回顾 | 晚间总结 |

## 推送格式

所有推送支持 Markdown 格式，在微信中会渲染为富文本。消息末尾统一标注来源。

## 注意事项

- Server酱免费版每天 5 条消息限制，注意不要频繁调用
- 如需更多配额可升级 Server酱会员或切换到 PushPlus
- 定时推送需要 Mac 处于开机状态（睡眠时 launchd 会在唤醒后补执行）
- 推送日志在 `/tmp/pa-daily-push-*.log`
