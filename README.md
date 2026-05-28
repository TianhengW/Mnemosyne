<p align="center">
  <img src="https://img.shields.io/badge/Platform-macOS-blue?style=flat-square&logo=apple" />
  <img src="https://img.shields.io/badge/Python-3.10+-yellow?style=flat-square&logo=python" />
  <img src="https://img.shields.io/badge/MCP_Tools-43-green?style=flat-square" />
  <img src="https://img.shields.io/badge/Skills-31-purple?style=flat-square" />
  <img src="https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square" />
</p>

# PA — Personal Research Assistant

> **Your Research Exocortex** — Remembers all your ideas, understands your full research landscape, and proactively tracks and connects knowledge.

A comprehensive personal research digital-twin system built on Claude Code + MCP protocol, covering paper management, knowledge tracking, experiment logging, writing management, focus analytics, automated notifications, and more.

**[中文文档](README_CN.md)**

---

## Architecture

```
PA/
├── mcp-servers/                  # MCP Server Cluster (9 independent services)
│   ├── zotero-server/            #   Zotero library interface
│   ├── obsidian-server/          #   Obsidian notes interface
│   ├── arxiv-server/             #   arXiv + HuggingFace paper tracking
│   ├── semantic-search-server/   #   Semantic search (Embedding + ChromaDB)
│   ├── proactive-server/         #   Deadline tracking + progress checks
│   ├── notify-server/            #   WeChat push (ServerChan)
│   ├── research-engine-server/   #   Research engine (35 tools)
│   ├── notion-server/            #   Notion knowledge base (bidirectional)
│   └── feishu-server/            #   Feishu/Lark meeting notes integration
├── scripts/                      # Standalone scripts (launchd scheduled)
│   ├── screen-monitor.py         #   Screen monitoring daemon
│   ├── daily-push.py             #   Scheduled push notifications
│   ├── feishu-poll.py            #   Feishu polling script
│   └── install.sh                #   One-click install/uninstall
├── skills/                       # Claude Code Skills (31)
├── launchd/                      # macOS launchd configs (6 scheduled tasks)
├── config/                       # Configuration files
│   ├── notify.json               #   Push config + research topic keywords
│   └── feishu.json               #   Feishu app configuration
├── CLAUDE.md                     # System instruction document
└── README.md
```

---

## Features

| Module | Capabilities | Key Technologies |
|--------|-------------|-----------------|
| 📚 **Literature Management** | Zotero full-library search, arXiv tracking, semantic search, Chrome reading tracking | SQLite, ChromaDB, Semantic Scholar API |
| 🧠 **Knowledge Management** | Five-layer memory pyramid, knowledge graph, spaced repetition, gap detection | SM-2 algorithm, regex concept extraction |
| 🔬 **Research Tracking** | Citation graph, research narrative, health dashboard, experiment journal | Semantic Scholar API, wandb |
| 🖥️ **Screen Monitoring** | Full screenshots + OCR, focus analytics, deep work detection | Apple Vision, SQLite FTS5 |
| ✍️ **Writing & Submission** | Writing progress tracking, submission pipeline, deadline dashboard | LaTeX parsing, SM pipeline |
| 📱 **Push Notifications** | WeChat scheduled push, paper recommendations, evening review | ServerChan API, launchd |
| 🤝 **Collaboration** | Feishu meeting notes, action items tracking | Feishu Open API |
| 📓 **Knowledge Base** | Notion bidirectional sync, search, create, query databases | Notion API |

---

## Feature Details

### 🖥️ 1. Screen Monitor — Full Activity Recording

A persistent daemon that captures the entire screen every 30 seconds, building a complete digital activity log.

**How it works:**

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────┐
│ screencapture│───▶│ Apple Vision │───▶│  SQLite DB  │───▶│FTS5 Search│
│  -x (silent) │    │ OCR (ZH+EN)  │    │ + screenshots│    │          │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────┘
       ▲                                       │
       │              osascript                 ▼
       └──── Get active window info ────── app_name + window_title
```

1. Uses macOS native `screencapture -x` for silent screenshots
2. Gets active app name and window title via `osascript`
3. Runs Apple Vision Framework OCR (Chinese + English)
4. Stores timestamp, app name, window title, OCR text in local SQLite
5. Screenshots organized by date; auto-cleaned after 7 days; OCR records retained 30 days

**Storage estimates:**

| Item | Size | Retention |
|------|------|-----------|
| Screenshots | ~2GB/day | 7 days (max ~14GB) |
| OCR database | ~200MB | 30 days |

**Use cases:**
- *"What paper was I reading this morning?"* → Full-text search OCR records
- *"How much time did I spend in VSCode this week?"* → Activity timeline query
- *"What was I doing at 3pm yesterday?"* → Timeline playback

```bash
uv run scripts/screen-monitor.py          # Foreground (debug)
uv run scripts/screen-monitor.py --once   # Single capture (test)
uv run scripts/screen-monitor.py --summary # Today's summary
```

---

### 🎯 2. Focus Analytics — Productivity Analysis

Quantifies your focus patterns and work efficiency based on Screen Monitor data.

**Dimensions:**

| Dimension | Description |
|-----------|-------------|
| 🧘 Deep Work Sessions | 10+ consecutive minutes in one app (flow state) |
| 🔄 Switch Frequency | App switches per hour → Focus Rating (A-D) |
| ⚠️ Distraction Detection | High-switch + short-dwell apps |
| ⏰ Peak Hours | Hours with most deep work |
| 📈 Weekly Trend | 7-day comparison: active time, deep work, switches |

**Rating Scale:**

| Rating | Switch Rate | Meaning |
|--------|-------------|---------|
| **A** 🟢 | < 5/h | Extreme focus (flow state) |
| **B** 🟡 | 5-10/h | Good focus |
| **C** 🟠 | 10-20/h | Moderate (room for improvement) |
| **D** 🔴 | > 20/h | Frequent switching (needs attention) |

<details>
<summary><b>Sample Output</b></summary>

```
## 🎯 Focus Analytics (2026-05-27)

Total active: 8.2h | Switches: 67 | Avg rate: 8.2/h
Focus Rating: B 🟡 (Good)

### 🧘 Deep Work Sessions (≥10min)
| Time  | App    | Duration |
|-------|--------|----------|
| 09:30 | VSCode | 45min    |
| 14:15 | Zotero | 28min    |
| 16:00 | VSCode | 32min    |

### ⏰ Peak Productivity Hours
- 09:00 — 52 min deep work
- 16:00 — 38 min deep work

### 📊 Hourly Switch Rate
09:00 | ████ (4)
10:00 | ████████ (8)
11:00 | ██████████████ (14)
14:00 | ██████ (6)
```

</details>

---

### 🕸️ 3. Citation Graph Explorer — Citation Network Exploration

Uses the Semantic Scholar API to expand a paper's citation network, helping discover important unread papers.

**Core capabilities:**

| Feature | Description |
|---------|-------------|
| 📥 Citations | Who cited this paper (downstream impact) |
| 📤 References | What this paper cites (upstream foundation) |
| ✅/📋 Zotero Cross-ref | Auto-marks read/unread status |
| 🏆 Unread Recommendations | High-citation unread papers, ranked by citation count |

**Use cases:**
- After reading a core paper, discover other important work in the area
- When writing Related Work, ensure no key citations are missed
- Find "bridge papers" connecting two sub-topics in the citation chain

**Input:** arXiv ID (e.g., `2301.12345`) or Semantic Scholar Paper ID

---

### 📖 4. Browser Reading Tracker — Academic Reading Tracking

Automatically parses Chrome browsing history to track academic reading behavior.

**How it works:**

```
Chrome History DB ──copy──▶ Temp copy ──filter──▶ Academic domains ──compare──▶ Zotero
                   (non-destructive)      (11 sites)                  (find unsaved)
```

**Covered academic sites:**

`arxiv.org` · `scholar.google.com` · `semanticscholar.org` · `openreview.net` · `paperswithcode.com` · `huggingface.co/papers` · `aclanthology.org` · `proceedings.neurips.cc` · `proceedings.mlr.press` · `ieeexplore.ieee.org` · `dl.acm.org`

**Core tools:**

| Tool | Description |
|------|-------------|
| `browser_reading_today()` | Today's academic browsing |
| `browser_reading_history(7)` | Reading trail for the past week |
| `browser_untracked_papers()` | Papers browsed but not added to Zotero |

---

### 💡 5. Contextual Recommendation — Context-Aware Suggestions

At the start of each new conversation, the system reads the last 30 minutes of screen activity and intelligently recommends relevant resources.

```
Screen Monitor (30min) ──▶ Extract keywords ──▶ Search Zotero + Obsidian ──▶ Recommend
```

| Detected Activity | Recommendation |
|-------------------|----------------|
| Reading a paper | Related papers and notes you've already read |
| Writing code | Relevant methodology notes and experiment records |
| Writing a paper | Citable literature |

**Integration:** Automatically invoked in the `/brain` skill — no manual trigger needed.

---

### 📜 6. Research Narrative Builder — Research Story Construction

Aggregates your research timeline from multiple data sources, generating a chronologically organized research story.

**Data source aggregation:**

```
Zotero (reading timeline)
    ├── decisions.md (decision nodes)
    ├── Experiments/ (experiment records)
    ├── Connections/ (cross-paper connections)
    └── idea-pool.md (idea evolution)
         │
         ▼
    Research Narrative (organized by month)
```

**Use cases:**
- Preparing a thesis proposal — trace how you arrived at your current direction
- Mid-term reports — show the logical chain of research progress
- Self-review — find the implicit main thread in your past 6 months of research

---

### ✍️ 7. Writing Tracker — Writing Progress Tracking

Tracks quantitative progress on paper writing, helping build a writing habit.

| Metric | Source | Description |
|--------|--------|-------------|
| 📊 Word count | .tex files | Filtered LaTeX commands |
| 📑 Section completion | `\section{}` | Percentage with substantive content |
| 📈 Daily trend | History records | Word count change curve |
| 🔥 Streak | Consecutive days | Motivation for consistent writing |

<details>
<summary><b>Sample Output</b></summary>

```
## ✍️ Writing Tracker: world-model-paper

Words: 4523 | Sections: 3/6 complete

### 📈 Word Count Trend
2026-05-24 | ████████ 1200
2026-05-25 | ██████████████ 2800
2026-05-26 | ██████████████████ 3600
2026-05-27 | ██████████████████████ 4523

Today: +923 words 📈
🔥 Writing streak: 4 days
```

</details>

---

### 📤 8. Submission Pipeline — Submission Lifecycle Management

Manages the complete lifecycle of a paper from idea to publication.

**Stage flow:**

```
💡 Idea ──▶ 📋 Outline ──▶ 📝 Draft ──▶ 🔍 Review ──▶ 📤 Submit ──▶ 📐 Camera Ready ──▶ 🎉 Published
```

**Each stage includes:**
- ✅ Status tracking (current stage)
- ☑️ Checklist (pre-submission/submission checks)
- 📝 Notes log (process notes and decisions)
- ⏰ Deadline countdown (color-coded urgency)

<details>
<summary><b>Dashboard Sample</b></summary>

```
## 📤 Submission Dashboard

| Paper           | Target       | Deadline   | Stage      | Remaining |
|-----------------|--------------|------------|------------|-----------|
| world-model-x   | NeurIPS 2026 | 2026-05-22 | 📝 draft   | 🔴 -5 days |
| concept-reason   | ICLR 2027    | 2026-10-01 | 💡 idea    | 🟢 127 days |
```

</details>

---

### 🧠 9. Knowledge Decay Alert — Spaced Repetition Tracking

Tracks your memory state for important papers using the SM-2 spaced repetition algorithm.

**Workflow:**

```
Zotero (papers with ≥3 annotations)
    │
    ▼
Knowledge Tracker ──SM-2 Algorithm──▶ Calculate next review date
    │
    ▼
Overdue paper list ──▶ Remind to review ──▶ Score (1-5) ──▶ Update interval
```

**SM-2 interval progression:**

| Review Quality | Effect | Example Interval |
|----------------|--------|------------------|
| 1-2 (forgot) | Interval resets | → 1 day |
| 3 (difficult recall) | Moderate growth | 7d → 12d |
| 4-5 (easy) | Significant growth | 7d → 15d → 38d → 95d |

---

### 🕸️ 10. Auto Knowledge Graph — Automatic Knowledge Graph

Automatically extracts research concepts and their relationships from paper annotations, building a queryable knowledge network.

**Construction pipeline:**

```
Zotero Annotations ──regex──▶ Concept Nodes ──co-occurrence──▶ Relation Edges ──JSON──▶ Knowledge Graph
(highlights+comments)  (30+ patterns)        (same paper)        (weight accumulation)
```

**Supported concept categories (30+):**

| Category | Examples |
|----------|----------|
| Methodologies | transformer, attention, diffusion model, RL |
| Paradigms | self-supervised, contrastive, few-shot, zero-shot |
| Research areas | world model, reasoning, vision-language, embodied |
| Techniques | RLHF, PPO, DPO, fine-tuning, knowledge distillation |

**Three query modes:**

| Tool | Function |
|------|----------|
| `knowledge_graph_build()` | Build/update the graph |
| `knowledge_graph_query("concept")` | View related papers and connections |
| `knowledge_graph_gaps()` | Discover isolated concepts and missing connections |

---

### 📈 11. Research Pulse — Research Health Dashboard

Multi-dimensional aggregation of research activity data, generating health reports and anomaly alerts.

| Dimension | Source | Meaning |
|-----------|--------|---------|
| 📄 Papers | Zotero `dateAdded` | New papers this week |
| 📝 Annotations | Zotero `itemAnnotations` | Annotation volume this week |
| 💻 Commits | `git log` | Code commits this week |
| 📒 Notes | Obsidian `mtime` | Note modifications this week |
| 🧪 Experiments | `Research/Experiments/` | New experiments this week |

**Alert rules:**
- ⚠️ No new papers for 2+ weeks → Reading pace anomaly
- ⚠️ No code commits for 2+ weeks → Possibly stuck
- ⚠️ No annotations for 2+ weeks → Reading depth issue

---

### 📱 12. WeChat Push System

Scheduled push notifications to WeChat via ServerChan API.

| Time | Type | Content |
|------|------|---------|
| 🌅 Daily 08:00 | Morning push | HuggingFace trending papers + deadline reminders |
| 🔄 Mon/Wed/Fri 10:00 | Knowledge review | Annotation cards from 2-8 weeks ago |
| 📈 Sunday 20:00 | Research pulse | Weekly research activity stats |
| 🌙 Daily 21:00 | Evening push | Screen activity + academic reading + code activity |

**Paper recommendation logic:** Filters 50 papers from HuggingFace Daily Papers by 8 research topic keywords, only pushing relevant ones.

---

### 🤝 13. Feishu Integration

```
Feishu Cloud Docs ──poll(30min)──▶ Structured Processing ──▶ Obsidian ──▶ WeChat notification
                                │
                                ▼
                        Action Items Tracking (pending → done / overdue)
```

---

## Quick Start

### Requirements

| Dependency | Version | Notes |
|------------|---------|-------|
| macOS | 14+ | Sonoma / Sequoia |
| Python | 3.10+ | System or Homebrew |
| [uv](https://github.com/astral-sh/uv) | latest | Package management (no pyproject.toml needed) |
| Claude Code | latest | CLI or IDE extension |
| Zotero | 7+ | Reference library |
| Obsidian | 1.5+ | Note-taking system |
| Chrome | any | Browser reading tracking |

### Installation

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone the project
git clone <repo-url> ~/Documents/Autolab/codes/PA
cd ~/Documents/Autolab/codes/PA

# 3. Configure ServerChan SendKey (get yours at: https://sct.ftqq.com/)
# Edit config/notify.json, fill in serverchan_sendkey

# 4. One-click install all scheduled tasks (auto-start on login)
bash scripts/install.sh

# 5. Grant Screen Recording permission
# System Settings → Privacy & Security → Screen Recording → enable your terminal app

# 6. Verify
uv run scripts/daily-push.py --type test   # Test WeChat push
uv run scripts/screen-monitor.py --once    # Test screen monitoring
bash scripts/install.sh --status           # Check service status
```

### Management Commands

```bash
bash scripts/install.sh            # Install all services
bash scripts/install.sh --status   # Check running status
bash scripts/install.sh --uninstall # Uninstall all services
```

---

## Scheduled Tasks

| Task | Frequency | Description |
|------|-----------|-------------|
| `com.pa.screen-monitor` | **KeepAlive** daemon | Screenshot + OCR (every 30s) |
| `com.pa.daily-push.morning` | Daily 08:00 | Paper recommendations + deadline alerts |
| `com.pa.daily-push.evening` | Daily 21:00 | Evening review (screen + reading + code) |
| `com.pa.resurfacing` | Mon/Wed/Fri 10:00 | Knowledge review cards |
| `com.pa.weekly-pulse` | Sunday 20:00 | Research health weekly report |
| `com.pa.feishu-poll` | Every 30 min | Feishu meeting notes polling |

> All tasks are macOS LaunchAgents — auto-start after user login, no manual intervention needed.

---

## MCP Tools (35)

<details>
<summary><b>Research Engine Server — Full List</b></summary>

| # | Tool | Description |
|---|------|-------------|
| 1 | `resurface_insights` | Knowledge review cards (2-8 week interval) |
| 2 | `mark_insight_connected` | Record cross-temporal knowledge connections |
| 3 | `find_connections` | Find cross-paper connections for a paper |
| 4 | `get_connection_map` | Get recorded connection graph |
| 5 | `create_experiment` | Create experiment record (wandb linked) |
| 6 | `update_experiment` | Update experiment status |
| 7 | `get_wandb_run` | Pull wandb run details |
| 8 | `list_experiments` | List experiments |
| 9 | `experiment_summary` | Experiment overview |
| 10 | `research_pulse` | Research health report |
| 11 | `pulse_alert` | Research anomaly detection |
| 12 | `screen_today_summary` | Today's screen activity summary |
| 13 | `screen_search` | Full-text search OCR records |
| 14 | `screen_timeline` | Activity timeline |
| 15 | `browser_reading_today` | Today's academic browsing |
| 16 | `browser_reading_history` | Academic reading history |
| 17 | `browser_untracked_papers` | Papers not saved to Zotero |
| 18 | `get_current_context` | Current screen activity context |
| 19 | `contextual_recommend` | Context-based recommendations |
| 20 | `build_narrative` | Research narrative construction |
| 21 | `research_timeline` | Research activity timeline |
| 22 | `focus_analytics` | Focus analysis |
| 23 | `focus_weekly_trend` | Weekly focus trend |
| 24 | `citation_graph` | Citation graph exploration |
| 25 | `citation_graph_unread` | Unread high-citation paper recommendations |
| 26 | `writing_track` | Writing progress tracking |
| 27 | `writing_status` | Writing project status overview |
| 28 | `create_submission` | Create submission pipeline |
| 29 | `update_submission` | Update submission stage |
| 30 | `submission_dashboard` | Submission dashboard |
| 31 | `knowledge_decay_check` | Knowledge decay check |
| 32 | `knowledge_review_done` | Mark review completed |
| 33 | `knowledge_graph_build` | Build knowledge graph |
| 34 | `knowledge_graph_query` | Query knowledge graph |
| 35 | `knowledge_graph_gaps` | Knowledge gap detection |

</details>

<details>
<summary><b>Notion Server — Full List</b></summary>

| # | Tool | Description |
|---|------|-------------|
| 1 | `notion_search` | Full-text search pages and databases |
| 2 | `notion_get_page` | Get page properties and body content |
| 3 | `notion_get_database` | Get database schema and entries |
| 4 | `notion_create_page` | Create new page (supports Markdown) |
| 5 | `notion_update_page` | Append content to existing page |
| 6 | `notion_list_databases` | List all accessible databases |
| 7 | `notion_query_database` | Query database with filters and sorts |
| 8 | `notion_list_pages` | List pages from database or all |

</details>

---

## Skills (31)

<table>
<tr><td>

**Digital Self Core (12)**

| Skill | Function |
|-------|----------|
| `/brain` | Exocortex control + contextual recommendations |
| `/digital-self` | Manage digital self system |
| `/memory-manage` | Memory management |
| `/notify` | WeChat push management |
| `/experiment` | Experiment journal |
| `/research-pulse` | Research health dashboard |
| `/meeting` | Meeting tracking |
| `/screen-activity` | Screen activity queries |
| `/narrative` | Research narrative |
| `/focus-analytics` | Focus analytics |
| `/citation-graph` | Citation graph |
| `/submission-pipeline` | Submission pipeline |

</td><td>

**Literature Management (11)**

| Skill | Function |
|-------|----------|
| `/paper-search` | Search papers |
| `/literature-review` | Literature review |
| `/research-note` | Paper notes |
| `/research-gap` | Research gaps |
| `/writing-assist` | Writing assistance |
| `/weekly-report` | Weekly report |
| `/paper-compare` | Paper comparison |
| `/idea-lab` | Idea management |
| `/advisor-prep` | Advisor meeting prep |
| `/explain-paper` | Paper explanation |
| `/reading-queue` | Reading queue |

</td></tr>
</table>

<details>
<summary><b>Code Development Skills (13)</b></summary>

`/exp-scaffold` `/train-debug` `/plot-figure` `/latex-table` `/slurm-job` `/ablation-plan` `/hf-helper` `/exp-config` `/model-analysis` `/code-release` `/repo-init` `/stat-test` `/demo-app`

</details>

---

## Data Storage

| Data | Location | Retention |
|------|----------|-----------|
| Screenshots | `~/.cache/pa-screen-monitor/screenshots/` | 7-day auto-cleanup |
| OCR text | `~/.cache/pa-screen-monitor/ocr.db` | 30-day auto-cleanup |
| Knowledge graph | `Obsidian Vault/Research/knowledge-graph.json` | Permanent |
| Knowledge decay | `Obsidian Vault/Research/knowledge-tracker.json` | Permanent |
| Experiments | `Obsidian Vault/Research/Experiments/` | Permanent |
| Writing tracking | `Obsidian Vault/Research/Writing/` | Permanent |
| Submissions | `Obsidian Vault/Research/Submissions/` | Permanent |
| Cross-paper links | `Obsidian Vault/Research/Connections/` | Permanent |
| Meeting notes | `Obsidian Vault/Research/Meetings/` | Permanent |

---

## Privacy

- All data is processed and stored **locally only**
- Screenshots and OCR are **never uploaded** to any server
- Apple Vision OCR runs completely offline
- ServerChan only sends text summaries (no screenshots)
- Chrome history uses copy-on-read mode — **never modifies** the original database
- Zotero uses a read-only cached copy

---

## Changelog

### `v0.5.0` — 2026-05-27 ✦ Intelligent Analytics & Knowledge Management

<table>
<tr><td>🎯</td><td><b>Focus Analytics</b></td><td>Deep work detection, switch frequency rating, distraction identification, hourly heatmap, weekly trends</td></tr>
<tr><td>🕸️</td><td><b>Citation Graph Explorer</b></td><td>Semantic Scholar API bidirectional exploration, Zotero cross-marking, unread high-citation recommendations</td></tr>
<tr><td>✍️</td><td><b>Writing Tracker</b></td><td>LaTeX word count, section completion, trend curves, writing streak</td></tr>
<tr><td>📤</td><td><b>Submission Pipeline</b></td><td>Idea→published 7-stage management, checklists, deadline countdown dashboard</td></tr>
<tr><td>🧠</td><td><b>Knowledge Decay Alert</b></td><td>SM-2 spaced repetition, auto-tracking important paper review cycles, quality scoring</td></tr>
<tr><td>🕸️</td><td><b>Auto Knowledge Graph</b></td><td>Concept auto-extraction (30+ patterns), co-occurrence relationship building, gap detection</td></tr>
</table>

> **+14 MCP tools** · **+3 Skills** (`/focus-analytics` `/citation-graph` `/submission-pipeline`)

---

### `v0.4.0` — 2026-05-27 ✦ Screen Monitoring & Passive Tracking

<table>
<tr><td>🖥️</td><td><b>Screen Monitor</b></td><td>macOS daemon — 30s screenshot + Apple Vision OCR, full screen activity recording</td></tr>
<tr><td>📖</td><td><b>Browser Reading Tracker</b></td><td>Chrome history parsing — 11 academic site filters, unsaved paper detection</td></tr>
<tr><td>💡</td><td><b>Contextual Recommendation</b></td><td>Context-aware recommendations based on last 30 minutes of screen activity</td></tr>
<tr><td>📜</td><td><b>Research Narrative Builder</b></td><td>Aggregates experiments/decisions/papers/ideas into monthly research stories</td></tr>
</table>

> **+8 MCP tools** · **+2 Skills** (`/screen-activity` `/narrative`) · **+1 daemon**

---

### `v0.3.0` — 2026-05-27 ✦ Research Engine & Collaboration

<table>
<tr><td>🔄</td><td><b>Spaced Resurfacing</b></td><td>Knowledge forgetting resistance — random review of 2-8 week old annotations</td></tr>
<tr><td>🔗</td><td><b>Cross-Paper Linker</b></td><td>Cross-paper connections — keyword matching + annotation comparison</td></tr>
<tr><td>🧪</td><td><b>Experiment Journal</b></td><td>Experiment logging — wandb integration, hypothesis validation tracking</td></tr>
<tr><td>📈</td><td><b>Research Pulse</b></td><td>Research health — 5-dimension aggregation + anomaly alerts</td></tr>
<tr><td>💬</td><td><b>Feishu Integration</b></td><td>Meeting notes structuring + action items tracking</td></tr>
</table>

> **+2 MCP Servers** · **+3 Skills** (`/experiment` `/research-pulse` `/meeting`)

---

### `v0.2.0` — 2026-05-27 ✦ Push Notification System

<table>
<tr><td>📱</td><td><b>WeChat Push</b></td><td>ServerChan WeChat push — paper recommendations, deadlines, work summaries, knowledge review, research pulse</td></tr>
<tr><td>⏰</td><td><b>Scheduled Tasks</b></td><td>macOS launchd scheduling — 6 automated tasks</td></tr>
</table>

> **+1 MCP Server** (`notify-server`) · **+3 scripts** · **+6 launchd configs**

---

### `v0.1.0` ✦ Foundation

- Zotero library integration (7 tools)
- Obsidian note management (6 tools)
- arXiv paper tracking (5 tools)
- Semantic search (3 tools)
- Deadline tracking + email drafting (6 tools)
- 31 Claude Code Skills

---

## License

Private project. Not for redistribution.
