---
name: digital-self
description: Manage the digital self system — update profile, record decisions, track goals
---

# Digital Self Manager

Manage your digital twin's self-knowledge: update profiles, record decisions, track goals, and evolve your digital self over time.

## Core Files (in Obsidian Vault)

```
Digital-Self/
├── Profile/
│   ├── personal-profile.md    # 个人基础信息
│   ├── research-positions.md  # 研究立场和观点
│   └── people-network.md      # 人际关系图谱
├── Memory/
│   ├── decision-log.md        # 重大决策记录
│   └── learning-trajectory.md # 学习成长轨迹
├── Goals/
│   └── goals.md               # 目标系统（博士里程碑→月→周）
└── Style/
    └── writing-style.md       # 写作风格参考
```

## Instructions

### Recording a Decision
When the user makes a research decision (direction change, paper choice, method selection):
1. Read `Digital-Self/Memory/decision-log.md`
2. Add a new entry at the top with: date, context, options, decision, rationale
3. Use `append_to_note` or direct edit

### Updating Goals
When goals change or are completed:
1. Read `Digital-Self/Goals/goals.md`
2. Update status, add new goals, move completed items
3. Check if weekly goals align with monthly/semester goals

### Updating Research Positions
When the user expresses a new opinion or changes their view:
1. Read `Digital-Self/Profile/research-positions.md`
2. Update the relevant section
3. Note what triggered the change

### Tracking Learning
When the user has an "aha moment" or masters something new:
1. Update `Digital-Self/Memory/learning-trajectory.md`
2. Record: what was learned, what triggered it, how it connects

### Before Responding as the User
When generating text "as the user" (emails, social posts, informal writing):
1. Read `Digital-Self/Style/writing-style.md`
2. Match their tone, vocabulary, and sentence patterns
3. Reference their research positions for opinions

## Proactive Behaviors

At the start of each session, Claude should:
1. Check if any goals have approaching deadlines
2. Note if the conversation reveals a decision worth logging
3. Watch for opinion changes or learning breakthroughs to record
4. Suggest updating stale profiles when relevant

## Philosophy

The digital self is not a static file — it's a living system that evolves with every interaction. When in doubt about what the user thinks or wants, CHECK these files rather than assuming. When the user reveals something new, UPDATE these files proactively.
