# Personal Research Assistant (PA) — Digital Self

个人科研数字分身系统。核心定位：**你的外脑**——记住你的一切想法、了解你的研究全貌、主动帮你追踪和串联知识。

用户是博一学生，研究方向：世界模型 (World Model)、概念推理 (Concept Reasoning)、VLM Reasoning。

## 数字分身架构 — 五层记忆金字塔

记忆按稳定性分层，越往上越稳定、越少更新：

```
Core (恒久) → Stable (年级) → Evolving (月级) → Working (周级) → Ephemeral (日级)
```

### Core — 恒久层（Digital-Self/Core/）
性格、世界观、认知风格。极少更新，仅重大人生转变时。
- `personality.md` — 性格特质、价值观、人生哲学、美学偏好、驱动模式
- `cognitive-style.md` — 学习方式、思维偏好、决策风格、沟通模式、精力管理

### Stable — 年级层（Digital-Self/Stable/）
研究品味、方法论偏好、长期目标、人际关系。每几个月更新。
- `research-taste.md` — 研究审美、方法论偏好、长期目标、合作风格
- `people.md` — 导师关系、核心人际网络、关键人物、沟通模板

### Evolving — 月级层（Digital-Self/Evolving/）
领域认知、技能水平、决策日志。读完重要论文/完成项目/做重大决策后更新。
- `domain-knowledge.md` — 各研究方向的当前认知水平和最近更新
- `skills-growth.md` — 技能等级（1-5）、突破记录
- `decisions.md` — 决策日志（背景→选项→决定→理由→回顾）

### Working — 周级层（Digital-Self/Working/）
当前阅读、活跃想法、近期洞察。每次对话中持续更新，每周整理。
- `current-context.md` — 本周论文阅读、活跃想法、卡点、目标
- `idea-pool.md` — 碎片想法池（Active / Parking Lot / Killed Ideas）

### Ephemeral — 日级层（Digital-Self/Ephemeral/）
今日待办、临时笔记。7天后自动清理。
- `today.md` — 待办、临时笔记、明日计划

### 记忆管理机制（详见 `/memory-manage`）
- **写入**: 对话中出现新信息时判断存入哪层
- **晋升**: 低层记忆验证后向上晋升（Working→Evolving→Stable）
- **衰减**: Ephemeral 7天清理，Working 4周未引用标记待整理
- **整合**: `/weekly-report` 时自动整合 Working→Evolving
- **检索**: 被问到话题时从 Core 到 Ephemeral 逐层查找

**重要**: 对话中检测到新洞察、决策、观点变化、新想法时，主动写入对应层。

## MCP Servers

### Zotero Server
访问 Zotero 文献库（~2000+ 论文），支持：
- `search_papers(query)` — 按标题/摘要/作者搜索
- `get_paper_details(paper_key)` — 获取论文完整元数据
- `get_annotations(paper_key)` — 获取高亮和批注
- `list_collections()` — 列出所有集合
- `get_collection_papers(collection_name)` — 获取集合内论文
- `get_recent_papers(days)` — 获取最近添加的论文
- `get_paper_tags(paper_key)` — 获取论文标签

### Obsidian Server
访问 Obsidian Vault 笔记，支持：
- `search_notes(query)` — 全文搜索
- `get_note(path)` — 读取笔记
- `list_notes(folder)` — 列出笔记
- `create_note(path, content, tags)` — 创建笔记
- `append_to_note(path, content)` — 追加内容
- `get_note_links(path)` — 获取双向链接

### arXiv Server
追踪最新论文动态：
- `search_arxiv(query)` — 搜索 arXiv 论文
- `get_arxiv_paper(arxiv_id)` — 获取 arXiv 论文详情
- `get_daily_papers(topic)` — 获取用户关注方向的最新论文
- `get_huggingface_daily_papers(date)` — 获取 HuggingFace 每日热门论文
- `track_research_topics()` — 查看配置的追踪主题

### Semantic Search Server
基于语义相似度搜索（Embedding + ChromaDB）：
- `semantic_search(query)` — 自然语言语义搜索论文库
- `find_similar_papers(paper_key)` — 查找与某篇论文相似的论文
- `get_index_stats()` — 查看索引状态

### Proactive Server
主动代理——deadline 追踪、进度检查、GitHub 集成：
- `check_deadlines(days_ahead)` — 查看即将到来的会议截止日期
- `add_deadline(name, deadline)` — 添加自定义 deadline
- `remove_deadline(name)` — 移除 deadline
- `git_activity_summary(repo_path, days)` — Git 活动摘要
- `progress_check()` — 综合进度检查（目标 + deadline）
- `draft_email(recipient, purpose)` — 起草学术邮件

### Notify Server
微信推送通知（通过 Server酱）：
- `send_wechat(title, content)` — 发送微信推送（支持 Markdown）
- `push_daily_papers()` — 聚合今日新论文并推送摘要
- `push_deadline_alert()` — 推送临近 deadline 提醒
- `push_work_summary(summary)` — 推送工作完成/进度通知
- `get_push_config()` — 查看推送配置
- `update_push_config(key, value)` — 修改推送设置

### Research Engine Server
研究引擎——知识回顾、跨论文连接、实验日志、研究脉搏、屏幕监控、浏览器追踪、叙事构建：
- `resurface_insights(days_ago_min, days_ago_max)` — 随机拉取旧 insight 生成回顾卡片
- `mark_insight_connected(paper_key, connection_note)` — 记录跨时间知识连接
- `find_connections(paper_key)` — 为论文寻找跨论文连接
- `get_connection_map(topic)` — 获取已记录的连接图谱
- `create_experiment(title, hypothesis, design, wandb_project, wandb_run_id)` — 创建实验记录
- `update_experiment(exp_id, status, conclusion)` — 更新实验状态
- `get_wandb_run(project, run_id)` — 从 wandb 拉取 run 详情
- `list_experiments(status)` — 列出实验
- `experiment_summary()` — 实验总览
- `research_pulse(weeks)` — 生成研究健康度报告
- `pulse_alert()` — 检查研究异常（适合推送）
- `screen_today_summary()` — 今日屏幕活动摘要（App 使用时间、主要活动）
- `screen_search(query, date)` — 全文搜索 OCR 记录
- `screen_timeline(date, hour_start, hour_end)` — 活动时间线
- `browser_reading_today()` — 今日浏览的学术论文
- `browser_reading_history(days)` — 最近 N 天学术阅读记录
- `browser_untracked_papers()` — 浏览过但未加入 Zotero 的论文
- `get_current_context()` — 获取当前屏幕活动上下文（最近 30 分钟）
- `contextual_recommend()` — 基于当前上下文推荐相关论文和笔记
- `build_narrative(topic, start_date, end_date)` — 为研究主题构建叙事时间线
- `research_timeline(months)` — 生成研究活动总时间线
- `focus_analytics(date)` — 专注度分析（深度工作、切换频率、分心应用）
- `focus_weekly_trend()` — 本周专注趋势
- `citation_graph(paper_id, direction, depth)` — 论文引用图谱（Semantic Scholar API）
- `citation_graph_unread(paper_id)` — 引用网络中未读的高引论文推荐
- `writing_track(project_name, tex_path)` — 追踪写作进度（词数、章节、趋势）
- `writing_status()` — 所有写作项目状态总览
- `create_submission(paper_title, target_venue, deadline, stage)` — 创建投稿管线
- `update_submission(paper_title, stage, note)` — 更新投稿阶段
- `submission_dashboard()` — 投稿仪表盘（所有项目进度和 deadline）
- `knowledge_decay_check()` — 知识衰减检查（间隔重复算法）
- `knowledge_review_done(paper_key, quality)` — 标记已回顾
- `knowledge_graph_build(limit)` — 构建/更新知识图谱
- `knowledge_graph_query(concept)` — 查询概念的关联论文和连接
- `knowledge_graph_gaps()` — 发现知识图谱中的 gap

### Feishu Server
飞书集成——会议纪要处理和 action items 追踪：
- `process_meeting_notes(content, title, participants)` — 结构化处理会议纪要
- `list_meetings(days)` — 列出近期会议记录
- `get_meeting(filename)` — 获取会议详情
- `check_action_items(status)` — 查看待办事项（pending/done/overdue）
- `complete_action_item(meeting_filename, item_text)` — 标记 action item 完成
- `fetch_feishu_doc(doc_url)` — 拉取飞书文档内容
- `get_feishu_config()` — 查看飞书配置状态

### Notion Server
Notion 知识库双向集成——搜索、读取、创建、查询：
- `notion_search(query, filter_type)` — 全文搜索 Notion 页面和数据库
- `notion_get_page(page_id)` — 获取页面完整内容（属性 + blocks 转 Markdown）
- `notion_get_database(database_id)` — 获取数据库结构和条目
- `notion_create_page(parent_id, title, content, parent_type, properties)` — 创建新页面（支持 Markdown 内容）
- `notion_update_page(page_id, content)` — 追加内容到现有页面
- `notion_list_databases()` — 列出所有可访问的数据库
- `notion_query_database(database_id, filter_json, sort_json)` — 按条件查询数据库
- `notion_list_pages(database_id)` — 列出页面（指定数据库或全部）

## Skills

### 数字分身核心
- `/brain` — 外脑总控（会话开始时回顾状态、上下文感知推荐、主动连接）
- `/digital-self` — 管理数字分身系统（更新档案、记录决策、追踪目标）
- `/memory-manage` — 记忆管理（写入、整合、晋升、衰减、检索）
- `/notify` — 微信推送管理（发送消息、配置推送、管理定时任务）
- `/experiment` — 实验日志（创建实验、关联 wandb、追踪假设验证）
- `/research-pulse` — 研究健康度仪表盘（多信号聚合、趋势预警）
- `/meeting` — 会后行动追踪（飞书纪要处理、action items 管理）
- `/screen-activity` — 屏幕活动查询（今日摘要、全文搜索、时间线）
- `/narrative` — 研究叙事构建（按主题/时间聚合研究历程）
- `/focus-analytics` — 专注度分析（深度工作时段、切换频率、分心检测、周趋势）
- `/citation-graph` — 引用图谱探索（Semantic Scholar 引用网络、未读论文发现）
- `/submission-pipeline` — 投稿管线管理（idea→发表全流程、deadline 追踪）

### 文献管理
- `/paper-search` — 搜索和浏览 Zotero 论文
- `/literature-review` — 对研究主题进行文献综述
- `/research-note` — 为论文生成结构化笔记并保存到 Obsidian
- `/research-gap` — 分析已读文献，发现研究空白和选题方向
- `/writing-assist` — 学术写作辅助（Related Work、找引用、润色）
- `/weekly-report` — 生成每周科研进展周报
- `/paper-compare` — 生成多篇论文的方法对比表
- `/idea-lab` — 结构化记录、发展和评估研究 idea
- `/advisor-prep` — 准备导师会议的议程和讨论要点
- `/explain-paper` — 深度解释论文方法、公式和贡献
- `/reading-queue` — 管理论文阅读队列和优先级

### 代码开发 Skills

- `/exp-scaffold` — 从论文描述生成实验代码骨架（model + train loop + config）
- `/train-debug` — 系统化诊断训练问题（NaN、OOM、收敛、速度）
- `/plot-figure` — 生成论文级 matplotlib/seaborn 图表
- `/latex-table` — 实验结果转 LaTeX 表格（自动加粗最优值）
- `/slurm-job` — 生成集群 SLURM 提交脚本（多GPU、sweep、依赖链）
- `/ablation-plan` — 设计消融实验矩阵并生成批量脚本
- `/hf-helper` — HuggingFace Transformers/PEFT/TRL 使用指南
- `/exp-config` — 管理实验配置，对比 runs，追踪超参
- `/model-analysis` — 模型行为分析（attention、梯度、特征、failure case）
- `/code-release` — 准备代码开源发布（README、LICENSE、cleanup）
- `/repo-init` — 初始化标准化 ML 研究项目结构
- `/stat-test` — 统计显著性检验（t-test、bootstrap CI、多重比较）
- `/demo-app` — 快速搭建 Gradio/Streamlit 交互演示

## 常用工作流

1. **了解研究进度**: 使用 `get_recent_papers` + `list_collections` 了解最近在看什么
2. **深入某篇论文**: `search_papers` → `get_paper_details` → `get_annotations`
3. **文献综述**: 用 `/literature-review` 汇总某个主题的已读论文
4. **做笔记**: 读完论文后用 `/research-note` 生成结构化笔记保存到 Obsidian
5. **追踪前沿**: `get_huggingface_daily_papers` 或 `get_daily_papers` 查看每日新论文
6. **语义探索**: `semantic_search("从经验中学习抽象概念")` 用自然语言找相关论文
7. **找选题**: 用 `/research-gap` 分析当前文献覆盖，发现潜在创新点
8. **写论文**: 用 `/writing-assist` 生成 Related Work，找引用支撑
9. **回顾今日**: 用 `/screen-activity` 查看今天的屏幕活动、使用了哪些 App、看了什么内容
10. **梳理研究历程**: 用 `/narrative` 按主题构建研究叙事时间线（适合开题/中期报告）
11. **发现遗漏论文**: `browser_untracked_papers()` 找出浏览过但没存到 Zotero 的论文
12. **专注度复盘**: 用 `/focus-analytics` 分析今日专注模式和深度工作时段
13. **拓展阅读**: 用 `/citation-graph` 从核心论文出发探索引用网络，发现未读关键论文
14. **投稿管理**: 用 `/submission-pipeline` 追踪论文从 idea 到发表的全流程
15. **知识巩固**: `knowledge_decay_check()` 检查哪些重要论文需要复习
16. **知识图谱**: `knowledge_graph_build()` 构建概念关系图，`knowledge_graph_gaps()` 发现知识盲区

## 追踪的研究方向

- world model
- concept reasoning
- VLM reasoning
- reinforcement learning reasoning
- test-time training
- self-evolving agent
- latent reasoning
- vision language action

## Obsidian Vault 结构

```
Obsidian Vault/
├── Digital-Self/
│   ├── Core/           # 恒久层：性格、世界观、认知风格
│   ├── Stable/         # 年级层：研究品味、人际关系
│   ├── Evolving/       # 月级层：领域认知、技能、决策
│   ├── Working/        # 周级层：当前阅读、活跃想法
│   └── Ephemeral/      # 日级层：今日待办、临时笔记
├── Papers/             # 论文阅读笔记
├── Research/           # 研究主题笔记
├── Daily/              # 日记/工作日志
└── Templates/          # 笔记模板
```

## 注意事项

- Zotero 数据库在 Zotero 运行时会被锁定，MCP server 使用缓存副本（60秒刷新）
- 论文 key 是 Zotero 内部标识符（如 GJJKUP6T），用于跨工具引用同一篇论文
- 语义搜索首次使用需要建立索引（会自动下载 embedding 模型约 90MB），后续使用会快很多
- arXiv API 有速率限制，避免短时间内大量请求
- Screen Monitor 需要 macOS「屏幕录制」权限，数据存储在 `~/.cache/pa-screen-monitor/`
- Chrome 历史数据库在 Chrome 运行时锁定，使用 copy-on-read 模式读取
- Screen Monitor 守护进程由 launchd 管理（`com.pa.screen-monitor`），截图保留 7 天，OCR 记录保留 30 天
