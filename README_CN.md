<p align="center">
  <img src="https://img.shields.io/badge/Platform-macOS-blue?style=flat-square&logo=apple" />
  <img src="https://img.shields.io/badge/Python-3.10+-yellow?style=flat-square&logo=python" />
  <img src="https://img.shields.io/badge/MCP_Tools-35-green?style=flat-square" />
  <img src="https://img.shields.io/badge/Skills-31-purple?style=flat-square" />
  <img src="https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square" />
</p>

# PA — Personal Research Assistant

> **你的科研外脑** — 记住你的一切想法、了解你的研究全貌、主动帮你追踪和串联知识。

基于 Claude Code + MCP 协议构建的全方位个人科研数字分身系统，覆盖论文管理、知识追踪、实验日志、写作管理、专注度分析、自动推送等功能。

---

## 📐 系统架构

```
PA/
├── mcp-servers/                  # MCP Server 集群（8 个独立服务）
│   ├── zotero-server/            #   Zotero 文献库接口
│   ├── obsidian-server/          #   Obsidian 笔记接口
│   ├── arxiv-server/             #   arXiv + HuggingFace 论文追踪
│   ├── semantic-search-server/   #   语义搜索（Embedding + ChromaDB）
│   ├── proactive-server/         #   Deadline 追踪 + 进度检查
│   ├── notify-server/            #   微信推送（Server酱）
│   ├── research-engine-server/   #   研究引擎（35 个 tools）
│   └── feishu-server/            #   飞书会议纪要集成
├── scripts/                      # 独立脚本（launchd 调度）
│   ├── screen-monitor.py         #   屏幕监控守护进程
│   ├── daily-push.py             #   定时推送脚本
│   ├── feishu-poll.py            #   飞书轮询脚本
│   └── install.sh                #   一键安装/卸载脚本
├── skills/                       # Claude Code Skills（31 个）
├── launchd/                      # macOS launchd 配置（6 个定时任务）
├── config/                       # 配置文件
│   ├── notify.json               #   推送配置 + 研究方向关键词
│   └── feishu.json               #   飞书应用配置
├── CLAUDE.md                     # 系统指令文档
└── README.md
```

---

## ✨ 功能总览

| 模块 | 功能 | 关键技术 |
|------|------|----------|
| 📚 **文献管理** | Zotero 全库搜索、arXiv 追踪、语义搜索、Chrome 阅读追踪 | SQLite, ChromaDB, Semantic Scholar API |
| 🧠 **知识管理** | 五层记忆金字塔、知识图谱、间隔重复、Gap 检测 | SM-2 算法, 正则概念提取 |
| 🔬 **研究追踪** | 引用图谱、研究叙事、健康度仪表盘、实验日志 | Semantic Scholar API, wandb |
| 🖥️ **屏幕监控** | 全量截图+OCR、专注度分析、深度工作检测 | Apple Vision, SQLite FTS5 |
| ✍️ **写作投稿** | 写作进度追踪、投稿管线、Deadline 仪表盘 | LaTeX 解析, SM pipeline |
| 📱 **推送通知** | 微信定时推送、论文推荐、晚间回顾 | Server酱 API, launchd |
| 🤝 **协作集成** | 飞书会议纪要、Action Items 追踪 | Feishu Open API |

---

## 🔍 功能详细介绍

### 🖥️ 1. Screen Monitor — 屏幕活动全量记录

长驻守护进程，每 30 秒对屏幕进行一次完整捕获，构建你的数字活动日志。

**工作原理:**

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────┐
│ screencapture│───▶│ Apple Vision │───▶│  SQLite DB  │───▶│ FTS5 搜索 │
│   -x (静默)  │    │  OCR (中+英)  │    │ + 截图存储   │    │          │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────┘
       ▲                                       │
       │              osascript                 ▼
       └──── 获取活动窗口信息 ────────────── app_name + window_title
```

1. 使用 macOS 原生 `screencapture -x` 静默截图（无快门声）
2. 通过 `osascript` 获取当前活动应用名称和窗口标题
3. 使用 Apple Vision Framework 对截图进行 OCR（支持中英双语）
4. 将时间戳、应用名、窗口标题、OCR 文本存入本地 SQLite 数据库
5. 截图按日期分目录存储，7 天后自动清理；OCR 记录保留 30 天

**存储估算:**

| 项目 | 大小 | 保留 |
|------|------|------|
| 截图 | ~2GB/天 | 7 天 (最大 ~14GB) |
| OCR 数据库 | ~200MB | 30 天 |

**使用场景:**
- *"我今天上午看了哪篇论文？"* → 全文搜索 OCR 记录
- *"我这周在 VSCode 里花了多少时间？"* → 活动时间线查询
- *"昨天下午 3 点我在干什么？"* → 时间线回溯

```bash
uv run scripts/screen-monitor.py          # 前台运行（调试）
uv run scripts/screen-monitor.py --once   # 单次捕获（测试）
uv run scripts/screen-monitor.py --summary # 今日摘要
```

---

### 🎯 2. Focus Analytics — 专注度分析

基于 Screen Monitor 采集的数据，量化你的专注模式和工作效率。

**分析维度:**

| 维度 | 说明 |
|------|------|
| 🧘 深度工作时段 | 连续 10+ 分钟在同一应用中（心流状态） |
| 🔄 切换频率 | 每小时 App 切换次数 → 专注评级 (A-D) |
| ⚠️ 分心检测 | 高切换频率 + 短停留时间的应用 |
| ⏰ 最高效时段 | 深度工作最集中的小时 |
| 📈 周趋势 | 7 天对比：活跃时间、深度工作、切换次数 |

**评级标准:**

| 评级 | 切换频率 | 含义 |
|------|----------|------|
| **A** 🟢 | < 5次/h | 极度专注（心流状态） |
| **B** 🟡 | 5-10次/h | 良好专注 |
| **C** 🟠 | 10-20次/h | 一般（建议改善） |
| **D** 🔴 | > 20次/h | 频繁切换（需关注） |

<details>
<summary><b>输出示例</b></summary>

```
## 🎯 Focus Analytics (2026-05-27)

总活跃时间: 8.2h | 切换次数: 67 | 平均切换频率: 8.2/h
专注评级: B 🟡 (良好)

### 🧘 深度工作时段 (≥10min)
| 时间  | 应用   | 持续    |
|-------|--------|---------|
| 09:30 | VSCode | 45min   |
| 14:15 | Zotero | 28min   |
| 16:00 | VSCode | 32min   |

### ⏰ 最高效时段
- 09:00 — 52 分钟深度工作
- 16:00 — 38 分钟深度工作

### 📊 每小时切换频率
09:00 | ████ (4)
10:00 | ████████ (8)
11:00 | ██████████████ (14)
14:00 | ██████ (6)
```

</details>

---

### 🕸️ 3. Citation Graph Explorer — 引用图谱探索

通过 Semantic Scholar API 展开论文的引用网络，帮你发现重要但还没读的论文。

**核心能力:**

| 功能 | 说明 |
|------|------|
| 📥 被引追踪 | 谁引用了这篇论文（下游影响） |
| 📤 参考文献 | 这篇论文引用了谁（上游基础） |
| ✅/📋 Zotero 交叉 | 自动标记已读/未读 |
| 🏆 未读推荐 | 高引但你没读的论文，按 citation count 排序 |

**使用场景:**
- 读完一篇核心论文后，想知道这个方向还有哪些重要工作
- 准备写 Related Work 时，确保没有遗漏关键引用
- 发现引用链中的"桥梁论文"（连接两个子方向的工作）

**输入:** arXiv ID（如 `2301.12345`）或 Semantic Scholar Paper ID

---

### 📖 4. Browser Reading Tracker — 浏览器学术阅读追踪

自动解析 Chrome 浏览历史，追踪你的学术阅读行为。

**工作原理:**

```
Chrome History DB ──copy──▶ 临时副本 ──filter──▶ 学术域名 ──compare──▶ Zotero
                   (不影响浏览器)          (11个站点)           (找出未保存的)
```

**覆盖的学术站点:**

`arxiv.org` · `scholar.google.com` · `semanticscholar.org` · `openreview.net` · `paperswithcode.com` · `huggingface.co/papers` · `aclanthology.org` · `proceedings.neurips.cc` · `proceedings.mlr.press` · `ieeexplore.ieee.org` · `dl.acm.org`

**核心功能:**
| Tool | 说明 |
|------|------|
| `browser_reading_today()` | 今天浏览了哪些学术内容 |
| `browser_reading_history(7)` | 最近一周的阅读轨迹 |
| `browser_untracked_papers()` | 浏览过但没加入 Zotero 的 arXiv 论文 |

---

### 💡 5. Contextual Recommendation — 上下文感知推荐

每次开始新对话时，系统读取最近 30 分钟的屏幕活动，智能推荐相关资源。

```
Screen Monitor (30min) ──▶ 提取关键词 ──▶ 搜索 Zotero + Obsidian ──▶ 推荐
```

| 检测到的活动 | 推荐内容 |
|-------------|----------|
| 在看论文 | 已读的相关论文和笔记 |
| 在写代码 | 相关方法论笔记和实验记录 |
| 在写论文 | 可引用的文献 |

**集成:** 在 `/brain` skill 中自动调用，无需手动触发。

---

### 📜 6. Research Narrative Builder — 研究叙事构建

从多个数据源聚合你的研究时间线，生成按时间排列的研究故事。

**数据源聚合:**

```
Zotero (阅读时间线)
    ├── decisions.md (决策节点)
    ├── Experiments/ (实验记录)
    ├── Connections/ (跨论文连接)
    └── idea-pool.md (想法演变)
         │
         ▼
    Research Narrative (按月组织的研究故事)
```

**适用场景:**
- 准备开题报告 — 梳理如何一步步走到当前研究方向
- 中期汇报 — 展示研究进展的逻辑链
- 自我回顾 — 找到过去半年研究轨迹中隐含的主线

---

### ✍️ 7. Writing Tracker — 写作进度追踪

追踪论文写作的量化进展，帮助建立写作习惯。

| 指标 | 来源 | 说明 |
|------|------|------|
| 📊 词数 | .tex 文件 | 过滤 LaTeX 命令后统计 |
| 📑 章节完成度 | `\section{}` | 检测有实质内容的比例 |
| 📈 每日趋势 | 历史记录 | 词数变化曲线 |
| 🔥 连续天数 | streak | 激励持续写作 |

<details>
<summary><b>输出示例</b></summary>

```
## ✍️ Writing Tracker: world-model-paper

Words: 4523 | Sections: 3/6 complete

### 📈 词数趋势
2026-05-24 | ████████ 1200
2026-05-25 | ██████████████ 2800
2026-05-26 | ██████████████████ 3600
2026-05-27 | ██████████████████████ 4523

今日新增: +923 words 📈
🔥 连续写作: 4 天
```

</details>

---

### 📤 8. Submission Pipeline — 投稿管线管理

管理论文从想法到发表的完整生命周期。

**阶段流程:**

```
💡 Idea ──▶ 📋 Outline ──▶ 📝 Draft ──▶ 🔍 Review ──▶ 📤 Submit ──▶ 📐 Camera Ready ──▶ 🎉 Published
```

**每个阶段包含:**
- ✅ 状态追踪（当前在哪个阶段）
- ☑️ Checklist（投稿前/投稿时检查项）
- 📝 Notes 日志（过程中的笔记和决策）
- ⏰ Deadline 倒计时（颜色编码紧急度）

<details>
<summary><b>Dashboard 示例</b></summary>

```
## 📤 Submission Dashboard

| 论文            | 目标          | Deadline   | 阶段       | 剩余     |
|-----------------|---------------|------------|------------|----------|
| world-model-x   | NeurIPS 2026 | 2026-05-22 | 📝 draft   | 🔴 -5天  |
| concept-reason   | ICLR 2027    | 2026-10-01 | 💡 idea    | 🟢 127天 |
```

</details>

---

### 🧠 9. Knowledge Decay Alert — 知识衰减提醒

基于间隔重复（SM-2 算法）追踪你对重要论文的记忆状态。

**工作流程:**

```
Zotero (≥3条批注的论文)
    │
    ▼
Knowledge Tracker ──SM-2 算法──▶ 计算下次复习日期
    │
    ▼
超期论文列表 ──▶ 提醒回顾 ──▶ 打分(1-5) ──▶ 更新间隔
```

**SM-2 间隔进化:**

| 回顾质量 | 效果 | 示例间隔 |
|----------|------|----------|
| 1-2 (忘了) | 间隔重置 | → 1天 |
| 3 (费力回忆) | 适度增长 | 7天 → 12天 |
| 4-5 (轻松) | 大幅增长 | 7天 → 15天 → 38天 → 95天 |

**vs Resurface 的区别:**

| | `resurface_insights` | `knowledge_decay_check` |
|--|--|--|
| 策略 | 随机回顾 | 针对性复习 |
| 目的 | 发现意外连接（探索性） | 巩固重要知识（系统性） |
| 触发 | 定时推送 | 主动检查 |

---

### 🕸️ 10. Auto Knowledge Graph — 自动知识图谱

从论文批注中自动提取研究概念及其关系，构建可查询的知识网络。

**构建流程:**

```
Zotero 批注 ──正则提取──▶ 概念节点 ──共现分析──▶ 关系边 ──JSON──▶ 知识图谱
(高亮+评论)    (30+模式)              (同篇论文)   (权重累加)
```

**支持的概念类别 (30+):**

| 类别 | 示例 |
|------|------|
| 方法论 | transformer, attention, diffusion model, RL |
| 范式 | self-supervised, contrastive, few-shot, zero-shot |
| 研究方向 | world model, reasoning, vision-language, embodied |
| 技术 | RLHF, PPO, DPO, fine-tuning, knowledge distillation |

**三种查询方式:**

| Tool | 功能 |
|------|------|
| `knowledge_graph_build()` | 构建/更新图谱 |
| `knowledge_graph_query("concept")` | 查看关联论文和连接 |
| `knowledge_graph_gaps()` | 发现孤立概念和缺失连接 |

---

### 📈 11. Research Pulse — 研究健康度仪表盘

多维度聚合研究活动数据，生成健康度报告和异常预警。

| 维度 | 数据源 | 含义 |
|------|--------|------|
| 📄 论文 | Zotero `dateAdded` | 本周新增论文数 |
| 📝 批注 | Zotero `itemAnnotations` | 本周标注量 |
| 💻 Commits | `git log` | 本周代码提交 |
| 📒 笔记 | Obsidian `mtime` | 本周笔记修改 |
| 🧪 实验 | `Research/Experiments/` | 本周新实验 |

**预警规则:**
- ⚠️ 连续 2 周无新论文 → 阅读节奏异常
- ⚠️ 连续 2 周无代码提交 → 可能卡住
- ⚠️ 连续 2 周无批注 → 阅读深度问题

---

### 📱 12. 微信推送系统

通过 Server酱 API 定时向微信推送研究相关信息。

| 时间 | 类型 | 内容 |
|------|------|------|
| 🌅 每天 08:00 | 早间推送 | HuggingFace 热门论文 + Deadline 提醒 |
| 🔄 周一/三/五 10:00 | 知识回顾 | 2-8 周前的论文批注卡片 |
| 📈 周日 20:00 | 研究脉搏 | 本周研究活动统计 |
| 🌙 每天 21:00 | 晚间推送 | 屏幕活动 + 学术阅读 + 代码活动 |

**论文推荐逻辑:** 从 HuggingFace Daily Papers（50 篇）中按 8 个研究方向关键词过滤，只推送相关论文。

---

### 🤝 13. 飞书集成

```
飞书云文档 ──poll(30min)──▶ 结构化处理 ──▶ Obsidian ──▶ 微信通知
                                │
                                ▼
                        Action Items 追踪 (pending → done / overdue)
```

---

## 🚀 快速开始

### 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| macOS | 14+ | Sonoma / Sequoia |
| Python | 3.10+ | 系统自带或 Homebrew |
| [uv](https://github.com/astral-sh/uv) | latest | 包管理（无需 pyproject.toml） |
| Claude Code | latest | CLI 或 IDE 扩展 |
| Zotero | 7+ | 文献库 |
| Obsidian | 1.5+ | 笔记系统 |
| Chrome | any | 浏览器阅读追踪 |

### Installation

```bash
# 1. 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 克隆项目
git clone <repo-url> ~/Documents/Autolab/codes/PA
cd ~/Documents/Autolab/codes/PA

# 3. 配置 Server酱 SendKey（获取: https://sct.ftqq.com/）
# 编辑 config/notify.json，填入 serverchan_sendkey

# 4. 一键安装所有定时任务（开机自启动）
bash scripts/install.sh

# 5. 授予屏幕录制权限
# System Settings → Privacy & Security → Screen Recording → 勾选终端应用

# 6. 验证
uv run scripts/daily-push.py --type test   # 测试微信推送
uv run scripts/screen-monitor.py --once    # 测试屏幕监控
bash scripts/install.sh --status           # 查看服务状态
```

### 管理命令

```bash
bash scripts/install.sh            # 安装全部服务
bash scripts/install.sh --status   # 查看运行状态
bash scripts/install.sh --uninstall # 卸载全部服务
```

---

## ⏰ 定时任务

| 任务 | 频率 | 说明 |
|------|------|------|
| `com.pa.screen-monitor` | **KeepAlive** 守护 | 屏幕截图 + OCR（每 30 秒） |
| `com.pa.daily-push.morning` | 每天 08:00 | 早间论文推荐 + Deadline 提醒 |
| `com.pa.daily-push.evening` | 每天 21:00 | 晚间回顾（屏幕活动 + 阅读 + 代码） |
| `com.pa.resurfacing` | 周一/三/五 10:00 | 知识回顾卡片 |
| `com.pa.weekly-pulse` | 周日 20:00 | 研究健康度周报 |
| `com.pa.feishu-poll` | 每 30 分钟 | 飞书会议纪要轮询 |

> 所有任务为 macOS LaunchAgent，用户登录后自动启动，无需手动干预。

---

## 🛠️ MCP Tools (35)

<details>
<summary><b>Research Engine Server — 完整列表</b></summary>

| # | Tool | 说明 |
|---|------|------|
| 1 | `resurface_insights` | 知识回顾卡片（间隔 2-8 周） |
| 2 | `mark_insight_connected` | 记录跨时间知识连接 |
| 3 | `find_connections` | 为论文寻找跨论文连接 |
| 4 | `get_connection_map` | 获取已记录的连接图谱 |
| 5 | `create_experiment` | 创建实验记录（关联 wandb） |
| 6 | `update_experiment` | 更新实验状态 |
| 7 | `get_wandb_run` | 拉取 wandb run 详情 |
| 8 | `list_experiments` | 列出实验 |
| 9 | `experiment_summary` | 实验总览 |
| 10 | `research_pulse` | 研究健康度报告 |
| 11 | `pulse_alert` | 研究异常检测 |
| 12 | `screen_today_summary` | 今日屏幕活动摘要 |
| 13 | `screen_search` | 全文搜索 OCR 记录 |
| 14 | `screen_timeline` | 活动时间线 |
| 15 | `browser_reading_today` | 今日学术浏览 |
| 16 | `browser_reading_history` | 学术阅读历史 |
| 17 | `browser_untracked_papers` | 未保存到 Zotero 的论文 |
| 18 | `get_current_context` | 当前屏幕上下文 |
| 19 | `contextual_recommend` | 上下文推荐 |
| 20 | `build_narrative` | 研究叙事构建 |
| 21 | `research_timeline` | 研究活动时间线 |
| 22 | `focus_analytics` | 专注度分析 |
| 23 | `focus_weekly_trend` | 周专注趋势 |
| 24 | `citation_graph` | 引用图谱探索 |
| 25 | `citation_graph_unread` | 未读高引论文推荐 |
| 26 | `writing_track` | 写作进度追踪 |
| 27 | `writing_status` | 写作项目状态 |
| 28 | `create_submission` | 创建投稿管线 |
| 29 | `update_submission` | 更新投稿进度 |
| 30 | `submission_dashboard` | 投稿仪表盘 |
| 31 | `knowledge_decay_check` | 知识衰减检查 |
| 32 | `knowledge_review_done` | 标记已回顾 |
| 33 | `knowledge_graph_build` | 构建知识图谱 |
| 34 | `knowledge_graph_query` | 查询知识图谱 |
| 35 | `knowledge_graph_gaps` | 知识 Gap 检测 |

</details>

---

## 🎮 Skills (31)

<table>
<tr><td>

**数字分身核心 (12)**

| Skill | 功能 |
|-------|------|
| `/brain` | 外脑总控 + 上下文推荐 |
| `/digital-self` | 管理数字分身 |
| `/memory-manage` | 记忆管理 |
| `/notify` | 微信推送管理 |
| `/experiment` | 实验日志 |
| `/research-pulse` | 研究健康度 |
| `/meeting` | 会议追踪 |
| `/screen-activity` | 屏幕活动 |
| `/narrative` | 研究叙事 |
| `/focus-analytics` | 专注度分析 |
| `/citation-graph` | 引用图谱 |
| `/submission-pipeline` | 投稿管线 |

</td><td>

**文献管理 (11)**

| Skill | 功能 |
|-------|------|
| `/paper-search` | 搜索论文 |
| `/literature-review` | 文献综述 |
| `/research-note` | 论文笔记 |
| `/research-gap` | 研究空白 |
| `/writing-assist` | 写作辅助 |
| `/weekly-report` | 周报 |
| `/paper-compare` | 论文对比 |
| `/idea-lab` | Idea 管理 |
| `/advisor-prep` | 导师会议 |
| `/explain-paper` | 论文解读 |
| `/reading-queue` | 阅读队列 |

</td></tr>
</table>

<details>
<summary><b>代码开发 Skills (13)</b></summary>

`/exp-scaffold` `/train-debug` `/plot-figure` `/latex-table` `/slurm-job` `/ablation-plan` `/hf-helper` `/exp-config` `/model-analysis` `/code-release` `/repo-init` `/stat-test` `/demo-app`

</details>

---

## 💾 数据存储

| 数据 | 位置 | 保留策略 |
|------|------|----------|
| 屏幕截图 | `~/.cache/pa-screen-monitor/screenshots/` | 7 天自动清理 |
| OCR 文本 | `~/.cache/pa-screen-monitor/ocr.db` | 30 天自动清理 |
| 知识图谱 | `Obsidian Vault/Research/knowledge-graph.json` | 永久 |
| 知识衰减 | `Obsidian Vault/Research/knowledge-tracker.json` | 永久 |
| 实验记录 | `Obsidian Vault/Research/Experiments/` | 永久 |
| 写作追踪 | `Obsidian Vault/Research/Writing/` | 永久 |
| 投稿管线 | `Obsidian Vault/Research/Submissions/` | 永久 |
| 跨论文连接 | `Obsidian Vault/Research/Connections/` | 永久 |
| 会议纪要 | `Obsidian Vault/Research/Meetings/` | 永久 |

---

## 🔒 隐私说明

- 所有数据**仅在本地**处理和存储
- 屏幕截图和 OCR **不上传**到任何服务器
- Apple Vision OCR 完全离线运行
- Server酱仅发送文字摘要（不含截图）
- Chrome 历史使用 copy-on-read 模式，**不修改**原数据库
- Zotero 使用只读缓存副本

---

## 📋 Changelog

### `v0.5.0` — 2026-05-27 ✦ 智能分析 & 知识管理

<table>
<tr><td>🎯</td><td><b>Focus Analytics</b></td><td>专注度分析 — 深度工作检测、切换频率评级、分心应用识别、每小时热力图、周趋势</td></tr>
<tr><td>🕸️</td><td><b>Citation Graph Explorer</b></td><td>引用图谱 — Semantic Scholar API 双向探索、Zotero 交叉标记、未读高引推荐</td></tr>
<tr><td>✍️</td><td><b>Writing Tracker</b></td><td>写作追踪 — LaTeX 词数统计、章节完成度、趋势曲线、连续写作 streak</td></tr>
<tr><td>📤</td><td><b>Submission Pipeline</b></td><td>投稿管线 — idea→published 7 阶段管理、Checklist、Deadline 倒计时仪表盘</td></tr>
<tr><td>🧠</td><td><b>Knowledge Decay Alert</b></td><td>知识衰减 — SM-2 间隔重复算法、自动追踪重要论文复习周期、质量打分</td></tr>
<tr><td>🕸️</td><td><b>Auto Knowledge Graph</b></td><td>知识图谱 — 概念自动提取 (30+ 模式)、共现关系构建、Gap 检测</td></tr>
</table>

> **+14 MCP tools** · **+3 Skills** (`/focus-analytics` `/citation-graph` `/submission-pipeline`)

---

### `v0.4.0` — 2026-05-27 ✦ 屏幕监控 & 被动追踪

<table>
<tr><td>🖥️</td><td><b>Screen Monitor</b></td><td>macOS 守护进程 — 每 30s 截图 + Apple Vision OCR、全量屏幕活动记录</td></tr>
<tr><td>📖</td><td><b>Browser Reading Tracker</b></td><td>Chrome 历史解析 — 11 个学术站点过滤、未保存论文检测</td></tr>
<tr><td>💡</td><td><b>Contextual Recommendation</b></td><td>上下文推荐 — 基于最近 30 分钟屏幕活动智能推荐论文和笔记</td></tr>
<tr><td>📜</td><td><b>Research Narrative Builder</b></td><td>研究叙事 — 从实验/决策/论文/想法聚合按月组织的研究故事</td></tr>
</table>

> **+8 MCP tools** · **+2 Skills** (`/screen-activity` `/narrative`) · **+1 守护进程**

---

### `v0.3.0` — 2026-05-27 ✦ 研究引擎 & 协作

<table>
<tr><td>🔄</td><td><b>Spaced Resurfacing</b></td><td>知识遗忘对抗 — 2-8 周前批注随机回顾</td></tr>
<tr><td>🔗</td><td><b>Cross-Paper Linker</b></td><td>跨论文连接 — 关键词匹配 + 批注对比</td></tr>
<tr><td>🧪</td><td><b>Experiment Journal</b></td><td>实验日志 — wandb 关联、假设验证追踪</td></tr>
<tr><td>📈</td><td><b>Research Pulse</b></td><td>研究健康度 — 5 维度聚合 + 异常预警</td></tr>
<tr><td>💬</td><td><b>Feishu Integration</b></td><td>飞书集成 — 会议纪要结构化 + Action Items</td></tr>
</table>

> **+2 MCP Servers** · **+3 Skills** (`/experiment` `/research-pulse` `/meeting`)

---

### `v0.2.0` — 2026-05-27 ✦ 推送通知系统

<table>
<tr><td>📱</td><td><b>WeChat Push</b></td><td>Server酱微信推送 — 论文推荐、Deadline、工作摘要、知识回顾、研究脉搏</td></tr>
<tr><td>⏰</td><td><b>Scheduled Tasks</b></td><td>macOS launchd 调度 — 6 个定时任务自动执行</td></tr>
</table>

> **+1 MCP Server** (`notify-server`) · **+3 脚本** · **+6 launchd 配置**

---

### `v0.1.0` ✦ 基础能力

- Zotero 文献库集成 (7 tools)
- Obsidian 笔记管理 (6 tools)
- arXiv 论文追踪 (5 tools)
- 语义搜索 (3 tools)
- Deadline 追踪 + 邮件起草 (6 tools)
- 31 个 Claude Code Skills

---

## License

Private project. Not for redistribution.
