# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]>=1.0.0", "httpx>=0.27.0", "wandb>=0.16.0"]
# ///

import json
import os
import random
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("research-engine")

ZOTERO_DB = os.environ.get("ZOTERO_DB", os.path.expanduser("~/Zotero/zotero.sqlite"))
OBSIDIAN_VAULT = os.environ.get("OBSIDIAN_VAULT", os.path.expanduser("~/Documents/Obsidian Vault"))
WANDB_ENTITY = os.environ.get("WANDB_ENTITY", "")
NOTIFY_CONFIG = os.environ.get("NOTIFY_CONFIG", os.path.expanduser("~/Documents/Autolab/codes/PA/config/notify.json"))

_db_cache_path = None
_db_cache_time = 0
DB_CACHE_TTL = 60


# ============================================================
# Utility: Zotero DB access (copy-on-read pattern)
# ============================================================

def _get_db_path() -> str:
    global _db_cache_path, _db_cache_time
    now = datetime.now().timestamp()
    if _db_cache_path and (now - _db_cache_time) < DB_CACHE_TTL:
        if Path(_db_cache_path).exists():
            return _db_cache_path

    tmp = os.path.join(tempfile.gettempdir(), "pa-research-engine-zotero.sqlite")
    shutil.copy2(ZOTERO_DB, tmp)
    _db_cache_path = tmp
    _db_cache_time = now
    return tmp


def _query_db(sql: str, params: tuple = ()) -> list[dict]:
    db_path = _get_db_path()
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ============================================================
# Feature 1: Spaced Resurfacing — 知识遗忘对抗
# ============================================================

@mcp.tool()
def resurface_insights(days_ago_min: int = 14, days_ago_max: int = 60, count: int = 3) -> str:
    """Randomly retrieve old annotations/highlights from papers read 2-8 weeks ago.
    Use this to combat forgetting and spark new connections with current work.
    Returns old insights paired with current research context for reflection.
    """
    date_min = (datetime.now() - timedelta(days=days_ago_max)).strftime("%Y-%m-%d")
    date_max = (datetime.now() - timedelta(days=days_ago_min)).strftime("%Y-%m-%d")

    sql = """
    SELECT ia.text, ia.comment, ia.dateAdded, i.key as paper_key,
           (SELECT value FROM itemData id2
            JOIN itemDataValues idv ON id2.valueID = idv.valueID
            JOIN fields f ON id2.fieldID = f.fieldID
            WHERE id2.itemID = i.itemID AND f.fieldName = 'title') as paper_title
    FROM itemAnnotations ia
    JOIN itemAttachments att ON ia.parentItemID = att.itemID
    JOIN items i ON att.parentItemID = i.itemID
    WHERE ia.dateAdded BETWEEN ? AND ?
      AND (ia.text IS NOT NULL OR ia.comment IS NOT NULL)
    ORDER BY RANDOM()
    LIMIT ?
    """

    try:
        results = _query_db(sql, (date_min, date_max, count * 3))
    except Exception as e:
        return f"❌ 数据库查询失败: {e}"

    if not results:
        return f"在 {days_ago_min}-{days_ago_max} 天前没有找到批注记录。"

    selected = random.sample(results, min(count, len(results)))

    # Read current context
    context_path = Path(OBSIDIAN_VAULT) / "Digital-Self" / "Working" / "current-context.md"
    current_focus = ""
    if context_path.exists():
        content = context_path.read_text()
        for line in content.split("\n"):
            if "活跃想法" in line or "正在" in line:
                current_focus += line + "\n"

    output = "## 🔄 知识回顾卡片\n\n"
    output += "*以下是你 2-8 周前读过的内容，试着和当前工作建立连接。*\n\n"

    for i, r in enumerate(selected, 1):
        days_ago = (datetime.now() - datetime.fromisoformat(r["dateAdded"].replace("Z", "+00:00").split("+")[0])).days
        output += f"### 卡片 {i} — {r.get('paper_title', '未知论文')} ({days_ago} 天前)\n"
        if r.get("text"):
            output += f"> {r['text'][:200]}\n"
        if r.get("comment"):
            output += f"\n📝 你的批注: {r['comment']}\n"
        output += f"\n🔑 Paper Key: `{r['paper_key']}`\n\n"

    if current_focus:
        output += "---\n### 💭 你当前的关注点\n" + current_focus + "\n"

    output += "---\n**反思提问**: 这些旧 insight 对你现在正在思考的问题有什么新启发？\n"
    return output


@mcp.tool()
def mark_insight_connected(paper_key: str, connection_note: str) -> str:
    """Record that an old insight has been connected to new knowledge.
    This helps track which old ideas have been integrated vs. forgotten.
    """
    connections_dir = Path(OBSIDIAN_VAULT) / "Research" / "Connections"
    connections_dir.mkdir(parents=True, exist_ok=True)

    log_path = connections_dir / "connection-log.md"
    today = datetime.now().strftime("%Y-%m-%d")

    entry = f"\n- [{today}] `{paper_key}` → {connection_note}\n"

    if log_path.exists():
        content = log_path.read_text()
    else:
        content = "# Connection Log\n\n跨时间的知识连接记录。\n"

    content += entry
    log_path.write_text(content)
    return f"✅ 已记录连接: {paper_key} → {connection_note}"


# ============================================================
# Feature 2: Cross-Paper Linker — 跨论文连接发现
# ============================================================

@mcp.tool()
def find_connections(paper_key: str) -> str:
    """Find potential connections between a paper and other papers in your library.
    Uses the paper's title and abstract to find semantically similar papers,
    then compares annotations to suggest connection points.
    """
    # Get target paper info
    sql_paper = """
    SELECT i.key, idv_title.value as title, idv_abs.value as abstract
    FROM items i
    LEFT JOIN itemData id_title ON i.itemID = id_title.itemID
    LEFT JOIN fields f_title ON id_title.fieldID = f_title.fieldID AND f_title.fieldName = 'title'
    LEFT JOIN itemDataValues idv_title ON id_title.valueID = idv_title.valueID
    LEFT JOIN itemData id_abs ON i.itemID = id_abs.itemID
    LEFT JOIN fields f_abs ON id_abs.fieldID = f_abs.fieldID AND f_abs.fieldName = 'abstractNote'
    LEFT JOIN itemDataValues idv_abs ON id_abs.valueID = idv_abs.valueID
    WHERE i.key = ?
    """

    try:
        papers = _query_db(sql_paper, (paper_key,))
    except Exception as e:
        return f"❌ 查询失败: {e}"

    if not papers:
        return f"未找到 paper_key={paper_key} 的论文"

    target = papers[0]
    title = target.get("title", "")
    abstract = target.get("abstract", "")

    if not title:
        return f"论文 {paper_key} 缺少标题信息"

    # Get annotations for the target paper
    sql_annotations = """
    SELECT ia.text, ia.comment
    FROM itemAnnotations ia
    JOIN itemAttachments att ON ia.parentItemID = att.itemID
    JOIN items i ON att.parentItemID = i.itemID
    WHERE i.key = ?
    AND (ia.text IS NOT NULL OR ia.comment IS NOT NULL)
    """
    target_annotations = _query_db(sql_annotations, (paper_key,))

    # Find similar papers by keyword overlap (simplified without semantic search)
    keywords = set()
    for word in (title + " " + (abstract or "")).lower().split():
        if len(word) > 4:
            keywords.add(word)

    if not keywords:
        return "无法提取论文关键词"

    # Search for papers with similar titles/abstracts
    keyword_conditions = " OR ".join(["idv.value LIKE ?" for _ in list(keywords)[:5]])
    keyword_params = tuple([f"%{kw}%" for kw in list(keywords)[:5]])

    sql_similar = f"""
    SELECT DISTINCT i.key, idv.value as title
    FROM items i
    JOIN itemData id ON i.itemID = id.itemID
    JOIN fields f ON id.fieldID = f.fieldID AND f.fieldName = 'title'
    JOIN itemDataValues idv ON id.valueID = idv.valueID
    WHERE i.key != ? AND ({keyword_conditions})
    LIMIT 10
    """

    try:
        similar = _query_db(sql_similar, (paper_key,) + keyword_params)
    except Exception as e:
        return f"❌ 相似论文搜索失败: {e}"

    if not similar:
        return "未找到相关论文。建议使用 semantic_search 工具做更精准的语义搜索。"

    # Get annotations for similar papers
    output = f"## 🔗 跨论文连接: {title}\n\n"
    output += f"找到 {len(similar)} 篇可能相关的论文：\n\n"

    for j, s in enumerate(similar[:5], 1):
        s_annotations = _query_db(sql_annotations, (s["key"],))
        output += f"### {j}. {s['title']}\n"
        output += f"**Key:** `{s['key']}`\n"
        if s_annotations:
            output += "**你的批注摘要:**\n"
            for ann in s_annotations[:3]:
                if ann.get("comment"):
                    output += f"  - 💭 {ann['comment'][:100]}\n"
                elif ann.get("text"):
                    output += f"  - 📌 {ann['text'][:100]}\n"
        output += "\n"

    if target_annotations:
        output += "---\n### 📝 当前论文的批注\n"
        for ann in target_annotations[:5]:
            if ann.get("comment"):
                output += f"- 💭 {ann['comment'][:150]}\n"
            elif ann.get("text"):
                output += f"- 📌 {ann['text'][:150]}\n"

    output += "\n---\n**建议**: 对比以上批注，思考这些论文之间有什么方法论或 insight 层面的连接。\n"
    output += "使用 `mark_insight_connected` 记录你发现的连接。\n"
    return output


@mcp.tool()
def get_connection_map(topic: str = "") -> str:
    """Get all recorded cross-paper connections, optionally filtered by topic."""
    log_path = Path(OBSIDIAN_VAULT) / "Research" / "Connections" / "connection-log.md"
    if not log_path.exists():
        return "暂无记录。使用 find_connections 和 mark_insight_connected 来建立连接。"

    content = log_path.read_text()
    if topic:
        lines = [l for l in content.split("\n") if topic.lower() in l.lower()]
        return f"## 与 '{topic}' 相关的连接\n\n" + "\n".join(lines) if lines else f"未找到与 '{topic}' 相关的连接记录"

    return content


# ============================================================
# Feature 3: Experiment Journal — 实验日志
# ============================================================

EXPERIMENTS_DIR = Path(OBSIDIAN_VAULT) / "Research" / "Experiments"


def _get_next_exp_id() -> str:
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(EXPERIMENTS_DIR.glob("EXP-*.md"))
    if not existing:
        return "EXP-001"
    nums = []
    for f in existing:
        try:
            nums.append(int(f.stem.split("-")[1]))
        except (IndexError, ValueError):
            pass
    next_num = max(nums) + 1 if nums else 1
    return f"EXP-{next_num:03d}"


@mcp.tool()
def create_experiment(
    title: str,
    hypothesis: str,
    design: str,
    wandb_project: str = "",
    wandb_run_id: str = "",
) -> str:
    """Create a new experiment journal entry.
    Links to a wandb run for automatic metric tracking.
    """
    exp_id = _get_next_exp_id()
    today = datetime.now().strftime("%Y-%m-%d")

    wandb_section = ""
    if wandb_project:
        entity = WANDB_ENTITY or "your-entity"
        run_url = f"https://wandb.ai/{entity}/{wandb_project}/runs/{wandb_run_id}" if wandb_run_id else "TBD"
        wandb_section = f"""## wandb
- Project: {wandb_project}
- Run ID: {wandb_run_id or 'TBD'}
- URL: {run_url}
- Status: 🏃 Running
"""

    content = f"""---
exp_id: {exp_id}
status: running
created: {today}
wandb_project: {wandb_project}
wandb_run_id: {wandb_run_id}
---

# {exp_id}: {title}

## 假设
{hypothesis}

## 实验设计
{design}

{wandb_section}
## 结果
| Metric | Value |
|--------|-------|
| | |

## 结论
[待实验完成后填写]

## 下一步
- [ ] 分析结果
- [ ] 决定是否继续这个方向
"""

    exp_path = EXPERIMENTS_DIR / f"{exp_id}-{title.replace(' ', '-')[:30]}.md"
    exp_path.write_text(content)
    return f"✅ 实验 {exp_id} 已创建: {exp_path.name}\n假设: {hypothesis[:80]}"


@mcp.tool()
def update_experiment(exp_id: str, status: str = "", conclusion: str = "", results: str = "") -> str:
    """Update an experiment's status, conclusion, or results.
    Status options: running, completed, failed, paused.
    """
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    matches = list(EXPERIMENTS_DIR.glob(f"{exp_id}*.md"))
    if not matches:
        return f"❌ 未找到实验 {exp_id}"

    exp_path = matches[0]
    content = exp_path.read_text()

    if status:
        status_emoji = {"running": "🏃", "completed": "✅", "failed": "❌", "paused": "⏸️"}.get(status, "❓")
        content = content.replace("status: running", f"status: {status}")
        content = content.replace("status: paused", f"status: {status}")
        content = content.replace("🏃 Running", f"{status_emoji} {status.capitalize()}")

    if conclusion:
        content = content.replace("[待实验完成后填写]", conclusion)

    if results:
        content = content.replace("| | |", results)

    exp_path.write_text(content)

    # If failed, suggest adding to killed ideas
    msg = f"✅ 实验 {exp_id} 已更新 (status={status})"
    if status == "failed":
        msg += "\n💡 提示: 考虑将失败原因记录到 Working/idea-pool.md 的 Killed Ideas 中"
    return msg


@mcp.tool()
def get_wandb_run(project: str, run_id: str) -> str:
    """Fetch run details from wandb (config, metrics, status).
    Requires WANDB_API_KEY to be configured.
    """
    try:
        import wandb
        api = wandb.Api()
    except ImportError:
        return "❌ wandb 未安装。请确保环境中有 wandb 包。"
    except Exception as e:
        return f"❌ wandb API 初始化失败: {e}"

    entity = WANDB_ENTITY
    try:
        run_path = f"{entity}/{project}/{run_id}" if entity else f"{project}/{run_id}"
        run = api.run(run_path)
    except Exception as e:
        return f"❌ 获取 run 失败: {e}\n路径: {run_path}"

    config_str = json.dumps(dict(run.config), indent=2, default=str)[:500]
    summary_str = json.dumps(dict(run.summary._json_dict), indent=2, default=str)[:500]

    return f"""## wandb Run: {run.name}

**Project:** {project}
**Run ID:** {run_id}
**State:** {run.state}
**URL:** {run.url}
**Created:** {run.created_at}
**Runtime:** {run.summary.get('_runtime', 'N/A')}s

### Config
```json
{config_str}
```

### Summary Metrics
```json
{summary_str}
```
"""


@mcp.tool()
def list_experiments(status: str = "") -> str:
    """List all experiments, optionally filtered by status (running/completed/failed/paused)."""
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    experiments = sorted(EXPERIMENTS_DIR.glob("EXP-*.md"))

    if not experiments:
        return "暂无实验记录。使用 create_experiment 创建第一个实验。"

    output = "## 📋 实验列表\n\n"
    output += "| ID | 标题 | 状态 | 创建日期 |\n|-----|------|------|----------|\n"

    for exp_path in experiments:
        content = exp_path.read_text()
        # Parse frontmatter
        exp_status = "unknown"
        created = "?"
        for line in content.split("\n")[:10]:
            if line.startswith("status:"):
                exp_status = line.split(":")[1].strip()
            if line.startswith("created:"):
                created = line.split(":")[1].strip()

        if status and exp_status != status:
            continue

        title_line = ""
        for line in content.split("\n"):
            if line.startswith("# EXP-"):
                title_line = line.replace("# ", "")
                break

        emoji = {"running": "🏃", "completed": "✅", "failed": "❌", "paused": "⏸️"}.get(exp_status, "❓")
        output += f"| {exp_path.stem.split('-')[0]}-{exp_path.stem.split('-')[1]} | {title_line[8:] if title_line else exp_path.stem} | {emoji} {exp_status} | {created} |\n"

    return output


@mcp.tool()
def experiment_summary() -> str:
    """Overview of all experiments: counts by status, recent completions, active runs."""
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    experiments = list(EXPERIMENTS_DIR.glob("EXP-*.md"))

    if not experiments:
        return "暂无实验记录。"

    counts = {"running": 0, "completed": 0, "failed": 0, "paused": 0, "unknown": 0}
    recent = []

    for exp_path in experiments:
        content = exp_path.read_text()
        exp_status = "unknown"
        created = ""
        for line in content.split("\n")[:10]:
            if line.startswith("status:"):
                exp_status = line.split(":")[1].strip()
            if line.startswith("created:"):
                created = line.split(":")[1].strip()
        counts[exp_status] = counts.get(exp_status, 0) + 1
        if exp_status == "running":
            recent.append((exp_path.stem, created))

    output = "## 📊 实验总览\n\n"
    output += f"- 🏃 进行中: {counts['running']}\n"
    output += f"- ✅ 已完成: {counts['completed']}\n"
    output += f"- ❌ 失败: {counts['failed']}\n"
    output += f"- ⏸️ 暂停: {counts['paused']}\n"
    output += f"- **总计**: {len(experiments)}\n"

    if recent:
        output += "\n### 当前在跑的实验\n"
        for name, date in recent:
            output += f"- {name} (started {date})\n"

    return output


# ============================================================
# Feature 4: Research Pulse — 研究健康度仪表盘
# ============================================================

@mcp.tool()
def research_pulse(weeks: int = 4) -> str:
    """Generate a research health report aggregating multiple signals:
    - Papers read (Zotero additions)
    - Code activity (git commits)
    - Annotations made
    - Experiments status
    - Notes written (Obsidian)
    """
    output = "## 📈 Research Pulse\n\n"
    today = datetime.now().date()

    weekly_data = []
    for w in range(weeks):
        week_end = today - timedelta(days=w * 7)
        week_start = week_end - timedelta(days=7)

        # Papers added
        sql_papers = """
        SELECT COUNT(*) as cnt FROM items i
        WHERE i.itemTypeID IN (SELECT itemTypeID FROM itemTypes WHERE typeName IN
            ('journalArticle','conferencePaper','preprint','report'))
        AND DATE(i.dateAdded) BETWEEN ? AND ?
        """
        try:
            paper_count = _query_db(sql_papers, (week_start.isoformat(), week_end.isoformat()))
            papers = paper_count[0]["cnt"] if paper_count else 0
        except Exception:
            papers = 0

        # Annotations made
        sql_ann = """
        SELECT COUNT(*) as cnt FROM itemAnnotations
        WHERE DATE(dateAdded) BETWEEN ? AND ?
        """
        try:
            ann_count = _query_db(sql_ann, (week_start.isoformat(), week_end.isoformat()))
            annotations = ann_count[0]["cnt"] if ann_count else 0
        except Exception:
            annotations = 0

        # Git commits
        git_commits = 0
        repos = [os.path.expanduser("~/Documents/Autolab/codes")]
        for repo in repos:
            if Path(repo).exists():
                try:
                    result = subprocess.run(
                        ["git", "log", f"--since={week_start}", f"--until={week_end}",
                         "--oneline", "--no-merges", "--all"],
                        capture_output=True, text=True, cwd=repo, timeout=10
                    )
                    git_commits += len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
                except Exception:
                    pass

        # Obsidian notes modified
        notes_count = 0
        papers_dir = Path(OBSIDIAN_VAULT) / "Papers"
        if papers_dir.exists():
            for note in papers_dir.rglob("*.md"):
                try:
                    mtime = datetime.fromtimestamp(note.stat().st_mtime).date()
                    if week_start <= mtime <= week_end:
                        notes_count += 1
                except Exception:
                    pass

        # Experiments
        exp_count = 0
        exp_dir = Path(OBSIDIAN_VAULT) / "Research" / "Experiments"
        if exp_dir.exists():
            for exp in exp_dir.glob("EXP-*.md"):
                try:
                    content = exp.read_text()
                    for line in content.split("\n")[:10]:
                        if line.startswith("created:"):
                            created = datetime.strptime(line.split(":")[1].strip(), "%Y-%m-%d").date()
                            if week_start <= created <= week_end:
                                exp_count += 1
                except Exception:
                    pass

        weekly_data.append({
            "week": f"{week_start} ~ {week_end}",
            "papers": papers,
            "annotations": annotations,
            "commits": git_commits,
            "notes": notes_count,
            "experiments": exp_count,
        })

    # Format report
    output += "| 周 | 📄 论文 | 📝 批注 | 💻 Commits | 📒 笔记 | 🧪 实验 |\n"
    output += "|-----|---------|---------|------------|---------|--------|\n"

    for i, w in enumerate(weekly_data):
        label = "本周" if i == 0 else f"{i}周前"
        output += f"| {label} | {w['papers']} | {w['annotations']} | {w['commits']} | {w['notes']} | {w['experiments']} |\n"

    # Alerts
    alerts = []
    if len(weekly_data) >= 2:
        this_week = weekly_data[0]
        last_week = weekly_data[1]
        if this_week["papers"] == 0 and last_week["papers"] == 0:
            alerts.append("⚠️ 连续 2 周没有新增论文，是否需要调整阅读计划？")
        if this_week["commits"] == 0 and last_week["commits"] == 0:
            alerts.append("⚠️ 连续 2 周没有代码提交，是否卡在某个问题上？")
        if this_week["annotations"] == 0 and last_week["annotations"] == 0:
            alerts.append("⚠️ 连续 2 周没有论文批注，是否在深度阅读？")

    if alerts:
        output += "\n### ⚠️ 预警\n" + "\n".join(alerts)
    else:
        output += "\n✅ 研究节奏正常"

    return output


@mcp.tool()
def pulse_alert() -> str:
    """Quick check for research anomalies — suitable for scheduled push notifications.
    Returns only alerts (no full report). Empty if everything is normal.
    """
    today = datetime.now().date()
    alerts = []

    for w_offset in range(2):
        week_end = today - timedelta(days=w_offset * 7)
        week_start = week_end - timedelta(days=7)

        sql_papers = """
        SELECT COUNT(*) as cnt FROM items i
        WHERE i.itemTypeID IN (SELECT itemTypeID FROM itemTypes WHERE typeName IN
            ('journalArticle','conferencePaper','preprint','report'))
        AND DATE(i.dateAdded) BETWEEN ? AND ?
        """
        try:
            result = _query_db(sql_papers, (week_start.isoformat(), week_end.isoformat()))
            if result[0]["cnt"] == 0 and w_offset == 1:
                alerts.append("连续低阅读量")
        except Exception:
            pass

    if not alerts:
        return ""

    return "⚠️ Research Pulse 预警: " + "; ".join(alerts)


# ============================================================
# Feature: Screen Monitor Tools — 屏幕活动查询
# ============================================================

SCREEN_DB = os.path.expanduser("~/.cache/pa-screen-monitor/ocr.db")


def _screen_db_query(sql: str, params: tuple = ()) -> list[dict]:
    if not Path(SCREEN_DB).exists():
        return []
    conn = sqlite3.connect(f"file:{SCREEN_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


@mcp.tool()
def screen_today_summary() -> str:
    """Get today's screen activity summary: app usage time, active windows, and key content."""
    today = datetime.now().strftime("%Y-%m-%d")

    app_rows = _screen_db_query(
        "SELECT app_name, COUNT(*) * 30 as seconds FROM screen_log WHERE timestamp LIKE ? AND app_name != '' GROUP BY app_name ORDER BY seconds DESC",
        (f"{today}%",)
    )

    total = _screen_db_query(
        "SELECT COUNT(*) as cnt FROM screen_log WHERE timestamp LIKE ?", (f"{today}%",)
    )

    titles = _screen_db_query(
        "SELECT DISTINCT window_title FROM screen_log WHERE timestamp LIKE ? AND window_title != '' ORDER BY timestamp DESC LIMIT 30",
        (f"{today}%",)
    )

    if not total or total[0]["cnt"] == 0:
        return "今日暂无屏幕活动记录。确保 screen-monitor 守护进程正在运行。"

    total_hours = total[0]["cnt"] * 30 / 3600
    output = f"## 📺 今日活动摘要\n\n**记录时间**: {total_hours:.1f}h\n\n"
    output += "### App 使用\n| App | 时间 |\n|-----|------|\n"
    for row in app_rows[:10]:
        m = row["seconds"] / 60
        if m >= 1:
            output += f"| {row['app_name']} | {m:.0f}min |\n"

    output += "\n### 活跃窗口\n"
    for t in titles[:15]:
        output += f"- {t['window_title'][:80]}\n"

    return output


@mcp.tool()
def screen_search(query: str, date: str = "") -> str:
    """Full-text search across OCR screen records. Finds when specific content appeared on screen.
    Date format: YYYY-MM-DD (empty = search all).
    """
    if date:
        rows = _screen_db_query(
            "SELECT s.timestamp, s.app_name, s.window_title, s.ocr_text FROM screen_log s JOIN screen_fts f ON s.id = f.rowid WHERE screen_fts MATCH ? AND s.timestamp LIKE ? ORDER BY s.timestamp DESC LIMIT 20",
            (query, f"{date}%")
        )
    else:
        rows = _screen_db_query(
            "SELECT s.timestamp, s.app_name, s.window_title, s.ocr_text FROM screen_log s JOIN screen_fts f ON s.id = f.rowid WHERE screen_fts MATCH ? ORDER BY s.timestamp DESC LIMIT 20",
            (query,)
        )

    if not rows:
        return f"未找到包含 '{query}' 的屏幕记录。"

    output = f"## 🔍 屏幕搜索: '{query}' ({len(rows)} 条结果)\n\n"
    for r in rows:
        ts = r["timestamp"][:19]
        output += f"**[{ts}]** {r['app_name']} — {r['window_title'][:60]}\n"
        # Show matching context
        text = r.get("ocr_text", "")
        if query.lower() in text.lower():
            idx = text.lower().find(query.lower())
            start = max(0, idx - 50)
            end = min(len(text), idx + len(query) + 50)
            snippet = text[start:end].replace("\n", " ")
            output += f"> ...{snippet}...\n\n"
        else:
            output += "\n"

    return output


@mcp.tool()
def screen_timeline(date: str = "") -> str:
    """Get activity timeline for a specific day (or today if empty).
    Shows what you did at each hour.
    """
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    rows = _screen_db_query(
        "SELECT timestamp, app_name, window_title FROM screen_log WHERE timestamp LIKE ? ORDER BY timestamp",
        (f"{date}%",)
    )

    if not rows:
        return f"{date} 没有活动记录。"

    # Group by hour
    hours: dict[str, list] = {}
    for r in rows:
        hour = r["timestamp"][11:13]
        if hour not in hours:
            hours[hour] = []
        entry = f"{r['app_name']}: {r['window_title'][:50]}" if r['window_title'] else r['app_name']
        if entry and entry not in hours[hour][-3:] if hours[hour] else True:
            hours[hour].append(entry)

    output = f"## 📅 活动时间线 ({date})\n\n"
    for hour in sorted(hours.keys()):
        unique_activities = list(dict.fromkeys(hours[hour]))[:5]
        output += f"### {hour}:00\n"
        for a in unique_activities:
            output += f"- {a}\n"
        output += "\n"

    return output


# ============================================================
# Feature: Browser Reading Tracker — 浏览器学术阅读
# ============================================================

CHROME_HISTORY = os.path.expanduser(
    "~/Library/Application Support/Google/Chrome/Default/History"
)

ACADEMIC_DOMAINS = [
    "arxiv.org",
    "scholar.google.com",
    "semanticscholar.org",
    "openreview.net",
    "paperswithcode.com",
    "huggingface.co/papers",
    "aclanthology.org",
    "proceedings.neurips.cc",
    "proceedings.mlr.press",
    "ieeexplore.ieee.org",
    "dl.acm.org",
]

_chrome_cache_path = None
_chrome_cache_time = 0


def _get_chrome_db() -> str:
    global _chrome_cache_path, _chrome_cache_time
    now = datetime.now().timestamp()
    if _chrome_cache_path and (now - _chrome_cache_time) < 60:
        if Path(_chrome_cache_path).exists():
            return _chrome_cache_path

    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "pa-chrome-history.sqlite")
    shutil.copy2(CHROME_HISTORY, tmp)
    _chrome_cache_path = tmp
    _chrome_cache_time = now
    return tmp


def _chrome_epoch_to_datetime(chrome_time: int) -> datetime:
    """Convert Chrome timestamp (microseconds since 1601-01-01) to datetime."""
    return datetime(1601, 1, 1) + timedelta(microseconds=chrome_time)


def _query_chrome(sql: str, params: tuple = ()) -> list[dict]:
    if not Path(CHROME_HISTORY).exists():
        return []
    db_path = _get_chrome_db()
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


@mcp.tool()
def browser_reading_today() -> str:
    """List academic papers browsed today in Chrome.
    Filters for arXiv, Scholar, OpenReview, and other academic sites.
    """
    today_start = datetime.now().replace(hour=0, minute=0, second=0)
    chrome_epoch_start = int((today_start - datetime(1601, 1, 1)).total_seconds() * 1_000_000)

    domain_conditions = " OR ".join([f"url LIKE '%{d}%'" for d in ACADEMIC_DOMAINS])
    sql = f"""
    SELECT DISTINCT url, title, last_visit_time, visit_count
    FROM urls
    WHERE last_visit_time > ? AND ({domain_conditions})
    ORDER BY last_visit_time DESC
    """

    rows = _query_chrome(sql, (chrome_epoch_start,))

    if not rows:
        return "今日暂无学术网站浏览记录。"

    output = "## 📖 今日学术阅读\n\n"
    output += f"共浏览 {len(rows)} 个学术页面：\n\n"

    # Group by domain
    by_domain: dict[str, list] = {}
    for r in rows:
        url = r["url"]
        for d in ACADEMIC_DOMAINS:
            if d in url:
                if d not in by_domain:
                    by_domain[d] = []
                by_domain[d].append(r)
                break

    for domain, papers in by_domain.items():
        output += f"### {domain} ({len(papers)})\n"
        for p in papers[:10]:
            title = p["title"][:80] if p["title"] else p["url"][:80]
            output += f"- {title}\n"
        output += "\n"

    return output


@mcp.tool()
def browser_reading_history(days: int = 7) -> str:
    """Get academic reading history from Chrome for the past N days."""
    start = datetime.now() - timedelta(days=days)
    chrome_epoch_start = int((start - datetime(1601, 1, 1)).total_seconds() * 1_000_000)

    domain_conditions = " OR ".join([f"url LIKE '%{d}%'" for d in ACADEMIC_DOMAINS])
    sql = f"""
    SELECT url, title, last_visit_time, visit_count
    FROM urls
    WHERE last_visit_time > ? AND ({domain_conditions})
    ORDER BY last_visit_time DESC
    LIMIT 100
    """

    rows = _query_chrome(sql, (chrome_epoch_start,))

    if not rows:
        return f"最近 {days} 天无学术浏览记录。"

    output = f"## 📖 学术阅读历史 (近{days}天)\n\n"

    # Group by day
    by_day: dict[str, list] = {}
    for r in rows:
        visit_dt = _chrome_epoch_to_datetime(r["last_visit_time"])
        day = visit_dt.strftime("%Y-%m-%d")
        if day not in by_day:
            by_day[day] = []
        by_day[day].append(r)

    for day in sorted(by_day.keys(), reverse=True):
        papers = by_day[day]
        output += f"### {day} ({len(papers)} 篇)\n"
        for p in papers[:8]:
            title = p["title"][:70] if p["title"] else "Untitled"
            output += f"- {title}\n"
        output += "\n"

    return output


@mcp.tool()
def browser_untracked_papers() -> str:
    """Find papers browsed in Chrome but NOT saved in Zotero.
    Helps you catch papers you looked at but forgot to save.
    """
    # Get recent academic URLs from Chrome
    days_back = 7
    start = datetime.now() - timedelta(days=days_back)
    chrome_epoch_start = int((start - datetime(1601, 1, 1)).total_seconds() * 1_000_000)

    sql = f"""
    SELECT DISTINCT url, title FROM urls
    WHERE last_visit_time > ? AND url LIKE '%arxiv.org/abs/%'
    ORDER BY last_visit_time DESC LIMIT 50
    """
    chrome_papers = _query_chrome(sql, (chrome_epoch_start,))

    if not chrome_papers:
        return "最近 7 天没有浏览 arXiv 论文。"

    # Extract arXiv IDs
    import re
    arxiv_ids = []
    for p in chrome_papers:
        match = re.search(r'arxiv\.org/abs/(\d{4}\.\d{4,5})', p["url"])
        if match:
            arxiv_ids.append({"id": match.group(1), "title": p["title"], "url": p["url"]})

    if not arxiv_ids:
        return "未提取到有效的 arXiv ID。"

    # Check which are in Zotero
    untracked = []
    for paper in arxiv_ids:
        sql_check = "SELECT COUNT(*) as cnt FROM itemDataValues WHERE value LIKE ?"
        try:
            result = _query_db(sql_check, (f"%{paper['id']}%",))
            if result[0]["cnt"] == 0:
                untracked.append(paper)
        except Exception:
            untracked.append(paper)

    if not untracked:
        return f"✅ 你浏览的 {len(arxiv_ids)} 篇 arXiv 论文都已在 Zotero 中。"

    output = f"## 📋 未保存论文 ({len(untracked)}/{len(arxiv_ids)} 篇)\n\n"
    output += "*这些论文你在浏览器中看过，但没有加入 Zotero：*\n\n"
    for p in untracked[:15]:
        title = p["title"].replace(" [", " — [") if p["title"] else p["id"]
        output += f"- **{title}**\n  arXiv: {p['id']} | [链接]({p['url']})\n\n"

    output += "\n💡 建议: 将有价值的论文加入 Zotero 以纳入知识库管理。"
    return output


# ============================================================
# Feature: Contextual Recommendation — 上下文感知推荐
# ============================================================

@mcp.tool()
def get_current_context() -> str:
    """Get current screen activity context (last 30 minutes).
    Returns active apps, window titles, and key content for contextual recommendations.
    """
    cutoff = (datetime.now() - timedelta(minutes=30)).isoformat()
    rows = _screen_db_query(
        "SELECT timestamp, app_name, window_title, ocr_text FROM screen_log WHERE timestamp > ? ORDER BY timestamp DESC LIMIT 20",
        (cutoff,)
    )

    if not rows:
        return "最近 30 分钟无屏幕记录。Screen Monitor 可能未在运行。"

    # Summarize context
    apps = set()
    titles = []
    keywords = set()

    for r in rows:
        if r["app_name"]:
            apps.add(r["app_name"])
        if r["window_title"] and r["window_title"] not in titles:
            titles.append(r["window_title"])
        # Extract potential research keywords from OCR
        if r.get("ocr_text"):
            text = r["ocr_text"].lower()
            research_terms = ["world model", "reasoning", "reinforcement", "transformer",
                            "attention", "embedding", "training", "inference", "agent",
                            "concept", "latent", "vision", "language"]
            for term in research_terms:
                if term in text:
                    keywords.add(term)

    output = "## 🎯 当前上下文\n\n"
    output += f"**活跃应用**: {', '.join(list(apps)[:5])}\n\n"
    output += "**最近窗口**:\n"
    for t in titles[:8]:
        output += f"- {t[:80]}\n"

    if keywords:
        output += f"\n**检测到研究关键词**: {', '.join(keywords)}\n"

    # Detect specific activities
    activities = []
    for t in titles:
        t_lower = t.lower()
        if "arxiv" in t_lower or "paper" in t_lower:
            activities.append("reading_paper")
        if ".py" in t_lower or ".ts" in t_lower or "vscode" in t_lower:
            activities.append("coding")
        if ".tex" in t_lower or "overleaf" in t_lower:
            activities.append("writing_paper")

    if activities:
        unique_acts = list(set(activities))
        output += f"\n**活动类型**: {', '.join(unique_acts)}\n"

    return output


@mcp.tool()
def contextual_recommend() -> str:
    """Based on current screen context, recommend relevant papers and notes from your library.
    Call this when starting a new conversation to get personalized context.
    """
    # Get current context
    cutoff = (datetime.now() - timedelta(minutes=30)).isoformat()
    rows = _screen_db_query(
        "SELECT window_title, ocr_text FROM screen_log WHERE timestamp > ? ORDER BY timestamp DESC LIMIT 10",
        (cutoff,)
    )

    if not rows:
        return "无法获取当前上下文，Screen Monitor 可能未在运行。"

    # Extract keywords from recent activity
    all_text = " ".join([r.get("window_title", "") + " " + (r.get("ocr_text", "") or "")[:200] for r in rows])
    keywords = set()
    research_terms = ["world model", "reasoning", "concept", "reinforcement learning",
                     "transformer", "attention", "VLM", "agent", "latent", "self-evolving",
                     "test-time", "vision language"]
    for term in research_terms:
        if term.lower() in all_text.lower():
            keywords.add(term)

    if not keywords:
        return "当前活动未检测到明确的研究关键词。"

    # Search Zotero for related papers
    output = f"## 💡 上下文推荐\n\n*基于你当前正在做的事（关键词: {', '.join(keywords)}）：*\n\n"

    for kw in list(keywords)[:3]:
        sql = """
        SELECT DISTINCT i.key,
               (SELECT value FROM itemData id2
                JOIN itemDataValues idv ON id2.valueID = idv.valueID
                JOIN fields f ON id2.fieldID = f.fieldID
                WHERE id2.itemID = i.itemID AND f.fieldName = 'title') as title
        FROM items i
        JOIN itemData id ON i.itemID = id.itemID
        JOIN itemDataValues idv ON id.valueID = idv.valueID
        WHERE idv.value LIKE ?
        LIMIT 5
        """
        try:
            papers = _query_db(sql, (f"%{kw}%",))
            if papers:
                output += f"### 📄 相关论文: {kw}\n"
                for p in papers[:3]:
                    if p.get("title"):
                        output += f"- {p['title'][:70]} (`{p['key']}`)\n"
                output += "\n"
        except Exception:
            pass

    # Check Obsidian for related notes
    notes_dir = Path(OBSIDIAN_VAULT) / "Papers"
    if notes_dir.exists():
        related_notes = []
        for kw in keywords:
            for note in notes_dir.rglob("*.md"):
                if kw.lower() in note.name.lower():
                    related_notes.append(note.name)

        if related_notes:
            output += "### 📒 相关笔记\n"
            for n in related_notes[:5]:
                output += f"- Papers/{n}\n"

    return output


# ============================================================
# Feature: Research Narrative Builder — 研究叙事构建
# ============================================================

@mcp.tool()
def build_narrative(topic: str, start_date: str = "", end_date: str = "") -> str:
    """Build a research narrative timeline for a given topic.
    Aggregates data from experiments, decisions, papers, and ideas to tell your research story.
    Date format: YYYY-MM-DD.
    """
    if not start_date:
        start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    output = f"# Research Narrative: {topic}\n"
    output += f"*Period: {start_date} ~ {end_date}*\n\n"

    # 1. Papers read on this topic
    sql_papers = """
    SELECT i.key, i.dateAdded,
           (SELECT value FROM itemData id2
            JOIN itemDataValues idv ON id2.valueID = idv.valueID
            JOIN fields f ON id2.fieldID = f.fieldID
            WHERE id2.itemID = i.itemID AND f.fieldName = 'title') as title
    FROM items i
    JOIN itemData id ON i.itemID = id.itemID
    JOIN itemDataValues idv ON id.valueID = idv.valueID
    WHERE idv.value LIKE ? AND i.dateAdded BETWEEN ? AND ?
    ORDER BY i.dateAdded
    LIMIT 30
    """
    try:
        papers = _query_db(sql_papers, (f"%{topic}%", start_date, end_date + "T23:59:59"))
        if papers:
            output += "## 📄 阅读轨迹\n\n"
            for p in papers:
                if p.get("title"):
                    date = p["dateAdded"][:10]
                    output += f"- [{date}] {p['title'][:70]} (`{p['key']}`)\n"
            output += "\n"
    except Exception:
        pass

    # 2. Experiments related to this topic
    exp_dir = Path(OBSIDIAN_VAULT) / "Research" / "Experiments"
    if exp_dir.exists():
        related_exps = []
        for exp in sorted(exp_dir.glob("EXP-*.md")):
            content = exp.read_text()
            if topic.lower() in content.lower():
                # Extract status and date
                status = "unknown"
                created = ""
                for line in content.split("\n")[:10]:
                    if line.startswith("status:"):
                        status = line.split(":")[1].strip()
                    if line.startswith("created:"):
                        created = line.split(":")[1].strip()
                related_exps.append((created, exp.stem, status))

        if related_exps:
            output += "## 🧪 实验记录\n\n"
            emoji_map = {"running": "🏃", "completed": "✅", "failed": "❌", "paused": "⏸️"}
            for date, name, status in related_exps:
                e = emoji_map.get(status, "❓")
                output += f"- [{date}] {e} {name}\n"
            output += "\n"

    # 3. Decisions from decisions.md
    decisions_path = Path(OBSIDIAN_VAULT) / "Digital-Self" / "Evolving" / "decisions.md"
    if decisions_path.exists():
        content = decisions_path.read_text()
        if topic.lower() in content.lower():
            output += "## 🔀 相关决策\n\n"
            in_relevant = False
            for line in content.split("\n"):
                if line.startswith("### ") and topic.lower() in line.lower():
                    in_relevant = True
                    output += f"{line}\n"
                elif in_relevant:
                    if line.startswith("### "):
                        break
                    if line.strip():
                        output += f"{line}\n"
            output += "\n"

    # 4. Connections
    conn_log = Path(OBSIDIAN_VAULT) / "Research" / "Connections" / "connection-log.md"
    if conn_log.exists():
        content = conn_log.read_text()
        related_conns = [l for l in content.split("\n") if topic.lower() in l.lower()]
        if related_conns:
            output += "## 🔗 发现的连接\n\n"
            for c in related_conns[:10]:
                output += f"{c}\n"
            output += "\n"

    # 5. Ideas from idea-pool
    idea_pool = Path(OBSIDIAN_VAULT) / "Digital-Self" / "Working" / "idea-pool.md"
    if idea_pool.exists():
        content = idea_pool.read_text()
        if topic.lower() in content.lower():
            output += "## 💡 相关想法\n\n"
            for line in content.split("\n"):
                if topic.lower() in line.lower() and line.strip().startswith("-"):
                    output += f"{line}\n"
            output += "\n"

    if len(output.split("\n")) < 10:
        output += f"\n*关于 '{topic}' 的记录较少。继续积累阅读和实验数据后，叙事会更丰富。*\n"

    return output


@mcp.tool()
def research_timeline(months: int = 6) -> str:
    """Generate overall research activity timeline for the past N months.
    Shows key milestones: papers read, experiments, decisions, ideas.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)

    output = f"## 📅 研究时间线 (近 {months} 个月)\n\n"

    # Monthly breakdown
    current = start_date
    while current < end_date:
        month_start = current.strftime("%Y-%m-%d")
        month_end = (current + timedelta(days=30)).strftime("%Y-%m-%d")
        month_label = current.strftime("%Y-%m")

        # Papers count
        try:
            papers = _query_db(
                "SELECT COUNT(*) as cnt FROM items WHERE dateAdded BETWEEN ? AND ?",
                (month_start, month_end)
            )
            paper_count = papers[0]["cnt"] if papers else 0
        except Exception:
            paper_count = 0

        # Experiments
        exp_count = 0
        exp_dir = Path(OBSIDIAN_VAULT) / "Research" / "Experiments"
        if exp_dir.exists():
            for exp in exp_dir.glob("EXP-*.md"):
                content = exp.read_text()[:200]
                if f"created: {month_label}" in content:
                    exp_count += 1

        if paper_count > 0 or exp_count > 0:
            output += f"### {month_label}\n"
            if paper_count:
                output += f"- 📄 新增 {paper_count} 篇论文\n"
            if exp_count:
                output += f"- 🧪 {exp_count} 个实验\n"
            output += "\n"

        current += timedelta(days=30)

    return output


# ============================================================
# Feature: Focus Analytics — 专注度分析
# ============================================================

@mcp.tool()
def focus_analytics(date: str = "") -> str:
    """Analyze focus patterns from screen monitor data.
    Shows: deep work sessions, app-switching frequency, distraction apps, optimal hours.
    Date format: YYYY-MM-DD (empty = today).
    """
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    rows = _screen_db_query(
        "SELECT timestamp, app_name, window_title FROM screen_log WHERE timestamp LIKE ? ORDER BY timestamp",
        (f"{date}%",)
    )

    if not rows:
        return f"{date} 没有活动记录。"

    # Analyze app switches
    switches = 0
    prev_app = ""
    hourly_switches: dict[str, int] = {}
    hourly_apps: dict[str, dict[str, int]] = {}
    deep_work_sessions = []
    current_session_start = None
    current_session_app = ""
    session_length = 0

    for r in rows:
        app = r["app_name"] or ""
        hour = r["timestamp"][11:13]

        if hour not in hourly_switches:
            hourly_switches[hour] = 0
            hourly_apps[hour] = {}

        if app not in hourly_apps[hour]:
            hourly_apps[hour][app] = 0
        hourly_apps[hour][app] += 1

        if app != prev_app and prev_app:
            switches += 1
            hourly_switches[hour] = hourly_switches.get(hour, 0) + 1

            if session_length >= 4:  # >= 2 minutes continuous on one app
                deep_work_sessions.append({
                    "app": current_session_app,
                    "start": current_session_start,
                    "duration_min": session_length * 0.5,
                })
            session_length = 0
            current_session_start = r["timestamp"]
            current_session_app = app
        else:
            session_length += 1
            if not current_session_start:
                current_session_start = r["timestamp"]
                current_session_app = app

        prev_app = app

    # Catch last session
    if session_length >= 4:
        deep_work_sessions.append({
            "app": current_session_app,
            "start": current_session_start,
            "duration_min": session_length * 0.5,
        })

    total_records = len(rows)
    total_hours = total_records * 30 / 3600
    avg_switches_per_hour = switches / max(total_hours, 0.1)

    # Identify distraction apps (high frequency, short duration)
    app_durations: dict[str, int] = {}
    app_switch_count: dict[str, int] = {}
    prev_app = ""
    for r in rows:
        app = r["app_name"] or ""
        app_durations[app] = app_durations.get(app, 0) + 1
        if app != prev_app and prev_app:
            app_switch_count[app] = app_switch_count.get(app, 0) + 1
        prev_app = app

    # Distraction score: high switch count relative to duration
    distractions = []
    for app, dur in app_durations.items():
        if not app:
            continue
        switch_freq = app_switch_count.get(app, 0)
        if dur >= 4 and switch_freq > 0:
            score = switch_freq / (dur * 0.5)  # switches per minute
            if score > 0.5:
                distractions.append((app, score, dur * 0.5))

    distractions.sort(key=lambda x: x[1], reverse=True)

    # Find most productive hour (longest deep work)
    hour_deep: dict[str, float] = {}
    for s in deep_work_sessions:
        h = s["start"][11:13] if s["start"] else "00"
        hour_deep[h] = hour_deep.get(h, 0) + s["duration_min"]

    # Build output
    output = f"## 🎯 Focus Analytics ({date})\n\n"
    output += f"**总活跃时间**: {total_hours:.1f}h | **切换次数**: {switches} | **平均切换频率**: {avg_switches_per_hour:.1f}/h\n\n"

    # Focus score (lower switch rate = better)
    if avg_switches_per_hour < 5:
        focus_grade = "A 🟢 (极度专注)"
    elif avg_switches_per_hour < 10:
        focus_grade = "B 🟡 (良好)"
    elif avg_switches_per_hour < 20:
        focus_grade = "C 🟠 (一般)"
    else:
        focus_grade = "D 🔴 (频繁切换)"
    output += f"**专注评级**: {focus_grade}\n\n"

    # Deep work sessions
    long_sessions = [s for s in deep_work_sessions if s["duration_min"] >= 10]
    if long_sessions:
        long_sessions.sort(key=lambda x: x["duration_min"], reverse=True)
        output += "### 🧘 深度工作时段 (≥10min)\n"
        output += "| 时间 | 应用 | 持续 |\n|------|------|------|\n"
        for s in long_sessions[:10]:
            start_time = s["start"][11:16] if s["start"] else "?"
            output += f"| {start_time} | {s['app']} | {s['duration_min']:.0f}min |\n"
        output += "\n"

    # Optimal hours
    if hour_deep:
        best_hours = sorted(hour_deep.items(), key=lambda x: x[1], reverse=True)[:3]
        output += "### ⏰ 最高效时段\n"
        for h, mins in best_hours:
            output += f"- {h}:00 — {mins:.0f} 分钟深度工作\n"
        output += "\n"

    # Distractions
    if distractions:
        output += "### ⚠️ 分心应用\n"
        for app, score, mins in distractions[:5]:
            output += f"- {app} (切换频率 {score:.1f}/min, 总 {mins:.0f}min)\n"
        output += "\n"

    # Hourly heatmap
    output += "### 📊 每小时切换频率\n"
    for h in sorted(hourly_switches.keys()):
        bar = "█" * min(hourly_switches[h], 20)
        output += f"{h}:00 | {bar} ({hourly_switches[h]})\n"

    return output


@mcp.tool()
def focus_weekly_trend() -> str:
    """Show weekly focus trends: daily deep work hours, switch frequency, and patterns."""
    output = "## 📈 本周专注趋势\n\n"
    output += "| 日期 | 活跃(h) | 深度工作(h) | 切换次数 | 评级 |\n"
    output += "|------|---------|-------------|----------|------|\n"

    for days_ago in range(6, -1, -1):
        date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        rows = _screen_db_query(
            "SELECT timestamp, app_name FROM screen_log WHERE timestamp LIKE ? ORDER BY timestamp",
            (f"{date}%",)
        )

        if not rows:
            output += f"| {date} | - | - | - | - |\n"
            continue

        total_hours = len(rows) * 30 / 3600
        switches = 0
        prev_app = ""
        session_length = 0
        deep_minutes = 0

        for r in rows:
            app = r["app_name"] or ""
            if app != prev_app and prev_app:
                switches += 1
                if session_length >= 4:
                    deep_minutes += session_length * 0.5
                session_length = 0
            else:
                session_length += 1
            prev_app = app

        if session_length >= 4:
            deep_minutes += session_length * 0.5

        deep_hours = deep_minutes / 60
        rate = switches / max(total_hours, 0.1)
        grade = "🟢" if rate < 5 else "🟡" if rate < 10 else "🟠" if rate < 20 else "🔴"
        output += f"| {date} | {total_hours:.1f} | {deep_hours:.1f} | {switches} | {grade} |\n"

    return output


# ============================================================
# Feature: Citation Graph Explorer — 引用图谱
# ============================================================

@mcp.tool()
def citation_graph(paper_id: str, direction: str = "both", depth: int = 1) -> str:
    """Explore citation network for a paper using Semantic Scholar API.
    paper_id: arXiv ID (e.g. '2301.12345') or Semantic Scholar paper ID.
    direction: 'citations' (who cites this), 'references' (what this cites), or 'both'.
    depth: 1 = direct connections only.
    Cross-references with your Zotero library to show which papers you've already read.
    """
    import httpx as _httpx

    base_url = "https://api.semanticscholar.org/graph/v1/paper"

    # Resolve paper ID
    if "/" not in paper_id and "." in paper_id:
        paper_id = f"arXiv:{paper_id}"

    fields = "title,authors,year,citationCount,url,externalIds"

    output = ""
    try:
        with _httpx.Client(timeout=30) as client:
            # Get paper info
            resp = client.get(f"{base_url}/{paper_id}", params={"fields": fields})
            if resp.status_code != 200:
                return f"❌ 未找到论文 '{paper_id}'。请确认 arXiv ID 或 Semantic Scholar ID 正确。"
            paper = resp.json()

            output = f"## 🕸️ Citation Graph: {paper.get('title', 'Unknown')}\n\n"
            output += f"**Year:** {paper.get('year', '?')} | **Citations:** {paper.get('citationCount', 0)}\n\n"

            # Get citations (papers that cite this one)
            if direction in ("citations", "both"):
                resp_cit = client.get(
                    f"{base_url}/{paper_id}/citations",
                    params={"fields": fields, "limit": 20}
                )
                if resp_cit.status_code == 200:
                    citations = resp_cit.json().get("data", [])
                    output += f"### 📥 被引用 ({len(citations)} shown)\n"
                    if citations:
                        for c in citations[:15]:
                            cp = c.get("citingPaper", {})
                            title = cp.get("title", "?")[:70]
                            year = cp.get("year", "?")
                            cit_count = cp.get("citationCount", 0)
                            arxiv_id = (cp.get("externalIds") or {}).get("ArXiv", "")
                            in_zotero = _check_in_zotero(title, arxiv_id)
                            marker = "✅" if in_zotero else "📋"
                            output += f"- {marker} [{year}] {title} (cited {cit_count}x)"
                            if arxiv_id:
                                output += f" `arXiv:{arxiv_id}`"
                            output += "\n"
                    else:
                        output += "*暂无引用记录*\n"
                    output += "\n"

            # Get references (papers this one cites)
            if direction in ("references", "both"):
                resp_ref = client.get(
                    f"{base_url}/{paper_id}/references",
                    params={"fields": fields, "limit": 20}
                )
                if resp_ref.status_code == 200:
                    references = resp_ref.json().get("data", [])
                    output += f"### 📤 参考文献 ({len(references)} shown)\n"
                    if references:
                        for r in references[:15]:
                            rp = r.get("citedPaper", {})
                            title = rp.get("title", "?")[:70]
                            year = rp.get("year", "?")
                            cit_count = rp.get("citationCount", 0)
                            arxiv_id = (rp.get("externalIds") or {}).get("ArXiv", "")
                            in_zotero = _check_in_zotero(title, arxiv_id)
                            marker = "✅" if in_zotero else "📋"
                            output += f"- {marker} [{year}] {title} (cited {cit_count}x)"
                            if arxiv_id:
                                output += f" `arXiv:{arxiv_id}`"
                            output += "\n"
                    else:
                        output += "*无参考文献数据*\n"
                    output += "\n"

    except _httpx.TimeoutException:
        return "❌ Semantic Scholar API 超时，请稍后重试。"
    except Exception as e:
        return f"❌ 引用图谱查询失败: {e}"

    output += "---\n✅ = 已在 Zotero | 📋 = 未收录\n"
    output += "💡 使用 `citation_graph_unread` 获取未读但高引用的推荐论文。"
    return output


def _check_in_zotero(title: str, arxiv_id: str = "") -> bool:
    """Check if a paper is already in Zotero library."""
    if arxiv_id:
        try:
            result = _query_db("SELECT COUNT(*) as cnt FROM itemDataValues WHERE value LIKE ?", (f"%{arxiv_id}%",))
            if result and result[0]["cnt"] > 0:
                return True
        except Exception:
            pass

    if title and len(title) > 10:
        try:
            short_title = title[:40]
            result = _query_db("SELECT COUNT(*) as cnt FROM itemDataValues WHERE value LIKE ?", (f"%{short_title}%",))
            if result and result[0]["cnt"] > 0:
                return True
        except Exception:
            pass

    return False


@mcp.tool()
def citation_graph_unread(paper_id: str) -> str:
    """Find highly-cited papers in the citation network that you haven't read yet.
    Useful for discovering important papers you might have missed.
    paper_id: arXiv ID or Semantic Scholar paper ID.
    """
    import httpx as _httpx

    base_url = "https://api.semanticscholar.org/graph/v1/paper"
    if "/" not in paper_id and "." in paper_id:
        paper_id = f"arXiv:{paper_id}"

    fields = "title,authors,year,citationCount,externalIds,abstract"

    unread_papers = []
    try:
        with _httpx.Client(timeout=30) as client:
            # Get references and citations
            for endpoint in ("references", "citations"):
                resp = client.get(
                    f"{base_url}/{paper_id}/{endpoint}",
                    params={"fields": fields, "limit": 30}
                )
                if resp.status_code != 200:
                    continue

                data = resp.json().get("data", [])
                for item in data:
                    p = item.get("citedPaper" if endpoint == "references" else "citingPaper", {})
                    if not p or not p.get("title"):
                        continue

                    arxiv_id = (p.get("externalIds") or {}).get("ArXiv", "")
                    if not _check_in_zotero(p["title"], arxiv_id):
                        unread_papers.append({
                            "title": p["title"],
                            "year": p.get("year", "?"),
                            "citations": p.get("citationCount", 0),
                            "arxiv_id": arxiv_id,
                            "abstract": (p.get("abstract") or "")[:150],
                            "source": endpoint,
                        })

    except Exception as e:
        return f"❌ 查询失败: {e}"

    if not unread_papers:
        return "✅ 引用网络中的论文你都已经在 Zotero 中了！"

    # Sort by citation count
    unread_papers.sort(key=lambda x: x["citations"], reverse=True)
    unread_papers = unread_papers[:15]

    output = f"## 📋 未读高引论文推荐\n\n"
    output += f"*从引用网络中发现 {len(unread_papers)} 篇你还没读的论文：*\n\n"

    for i, p in enumerate(unread_papers, 1):
        output += f"### {i}. {p['title'][:70]}\n"
        output += f"**Year:** {p['year']} | **Citations:** {p['citations']} | **来源:** {'被引' if p['source'] == 'citations' else '参考文献'}\n"
        if p["arxiv_id"]:
            output += f"**arXiv:** {p['arxiv_id']}\n"
        if p["abstract"]:
            output += f"> {p['abstract']}...\n"
        output += "\n"

    output += "💡 建议: 优先阅读引用量高的论文，它们可能是这个方向的关键工作。"
    return output


# ============================================================
# Feature: Writing Tracker — 写作进度追踪
# ============================================================

WRITING_PROJECTS_DIR = Path(OBSIDIAN_VAULT) / "Research" / "Writing"


@mcp.tool()
def writing_track(project_name: str, tex_path: str = "") -> str:
    """Track writing progress for a paper/document.
    project_name: Name of the writing project.
    tex_path: Path to .tex file to analyze (optional, will count words/sections).
    """
    WRITING_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    project_file = WRITING_PROJECTS_DIR / f"{project_name.replace(' ', '-')}.md"

    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")

    # Analyze tex file if provided
    tex_stats = ""
    word_count = 0
    sections_done = 0
    sections_total = 0

    if tex_path and Path(tex_path).exists():
        content = Path(tex_path).read_text()
        # Word count (rough: exclude LaTeX commands)
        import re
        text_only = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', content)
        text_only = re.sub(r'\\[a-zA-Z]+', '', text_only)
        text_only = re.sub(r'[{}\\%$]', '', text_only)
        word_count = len(text_only.split())

        # Count sections
        sections = re.findall(r'\\section\{([^}]+)\}', content)
        sections_total = len(sections)
        # Sections with content (more than just the header)
        for sec in sections:
            sec_pattern = rf'\\section\{{{re.escape(sec)}\}}(.*?)(?=\\section|\\end\{{document\}})'
            match = re.search(sec_pattern, content, re.DOTALL)
            if match and len(match.group(1).strip()) > 100:
                sections_done += 1

        tex_stats = f"\n**Words:** {word_count} | **Sections:** {sections_done}/{sections_total} complete\n"

    # Read or create project tracking file
    if project_file.exists():
        tracking = project_file.read_text()
    else:
        tracking = f"""---
project: {project_name}
created: {today}
status: drafting
---

# Writing Tracker: {project_name}

## Progress Log

"""

    # Append today's entry
    entry = f"- [{today} {now_time}] words={word_count}"
    if sections_total:
        entry += f" sections={sections_done}/{sections_total}"
    entry += "\n"

    if f"[{today}" not in tracking:
        tracking += entry
    else:
        # Update today's latest entry
        lines = tracking.split("\n")
        for i, line in enumerate(lines):
            if f"[{today}" in line:
                lines[i] = entry.rstrip()
                break
        tracking = "\n".join(lines)

    project_file.write_text(tracking)

    # Calculate progress
    output = f"## ✍️ Writing Tracker: {project_name}\n\n"
    if tex_stats:
        output += tex_stats + "\n"

    # Parse historical data for trend
    import re
    entries = re.findall(r'\[(\d{4}-\d{2}-\d{2})[^\]]*\] words=(\d+)', tracking)
    if len(entries) >= 2:
        output += "### 📈 词数趋势\n"
        for date_str, wc in entries[-7:]:
            bar_len = int(int(wc) / 200)
            bar = "█" * min(bar_len, 30)
            output += f"{date_str} | {bar} {wc}\n"
        output += "\n"

        # Daily growth
        if len(entries) >= 2:
            latest = int(entries[-1][1])
            previous = int(entries[-2][1])
            delta = latest - previous
            if delta > 0:
                output += f"**今日新增**: +{delta} words 📈\n"
            elif delta < 0:
                output += f"**今日变化**: {delta} words (可能在编辑/删减)\n"

    # Writing streak
    streak_days = 0
    for i in range(30):
        check_date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        if check_date in tracking:
            streak_days += 1
        else:
            break

    if streak_days > 1:
        output += f"\n🔥 **连续写作**: {streak_days} 天\n"

    return output


@mcp.tool()
def writing_status() -> str:
    """Show status of all tracked writing projects."""
    WRITING_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    projects = list(WRITING_PROJECTS_DIR.glob("*.md"))

    if not projects:
        return "暂无写作项目。使用 `writing_track(project_name, tex_path)` 开始追踪。"

    output = "## ✍️ 写作项目状态\n\n"
    output += "| 项目 | 状态 | 最后更新 | 词数 |\n|------|------|----------|------|\n"

    import re
    for pf in sorted(projects):
        content = pf.read_text()
        status = "drafting"
        for line in content.split("\n")[:10]:
            if line.startswith("status:"):
                status = line.split(":")[1].strip()

        entries = re.findall(r'\[(\d{4}-\d{2}-\d{2})[^\]]*\] words=(\d+)', content)
        last_date = entries[-1][0] if entries else "?"
        last_words = entries[-1][1] if entries else "0"

        emoji = {"drafting": "📝", "reviewing": "🔍", "submitted": "📤", "accepted": "🎉"}.get(status, "❓")
        output += f"| {pf.stem} | {emoji} {status} | {last_date} | {last_words} |\n"

    return output


# ============================================================
# Feature: Submission Pipeline — 投稿管线
# ============================================================

SUBMISSIONS_DIR = Path(OBSIDIAN_VAULT) / "Research" / "Submissions"


@mcp.tool()
def create_submission(
    paper_title: str,
    target_venue: str,
    deadline: str,
    stage: str = "idea",
) -> str:
    """Create a new submission pipeline entry.
    stage: idea → outline → draft → internal_review → submit → camera_ready → published
    deadline format: YYYY-MM-DD
    """
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    slug = paper_title.replace(" ", "-")[:40].lower()
    sub_file = SUBMISSIONS_DIR / f"{slug}.md"

    content = f"""---
title: {paper_title}
venue: {target_venue}
deadline: {deadline}
stage: {stage}
created: {today}
---

# {paper_title}

**Target:** {target_venue} (deadline: {deadline})

## Pipeline

- [{'x' if stage == 'idea' else ' '}] 💡 Idea — 确定研究问题和方向
- [ ] 📋 Outline — 完成论文大纲和实验计划
- [ ] 📝 Draft — 完成初稿
- [ ] 🔍 Internal Review — 内部审阅和修改
- [ ] 📤 Submit — 投稿
- [ ] 📐 Camera Ready — 终稿
- [ ] 🎉 Published

## Checklist

### 投稿前
- [ ] 实验结果完整
- [ ] 图表清晰规范
- [ ] Related Work 完善
- [ ] Abstract 精炼
- [ ] 导师审阅通过

### 投稿时
- [ ] 格式符合要求
- [ ] 补充材料准备
- [ ] 作者信息确认
- [ ] 匿名化检查（如需要）

## Notes

"""

    sub_file.write_text(content)

    days_left = (datetime.strptime(deadline, "%Y-%m-%d").date() - datetime.now().date()).days
    return f"✅ 投稿管线已创建: {paper_title}\n目标: {target_venue} | 距截止 {days_left} 天 | 当前阶段: {stage}"


@mcp.tool()
def update_submission(paper_title: str, stage: str = "", note: str = "") -> str:
    """Update a submission's stage or add notes.
    stage options: idea, outline, draft, internal_review, submit, camera_ready, published
    """
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Find matching submission
    matches = []
    for f in SUBMISSIONS_DIR.glob("*.md"):
        if paper_title.lower().replace(" ", "-") in f.stem.lower():
            matches.append(f)
        else:
            content = f.read_text()
            if paper_title.lower() in content.lower()[:200]:
                matches.append(f)

    if not matches:
        return f"❌ 未找到匹配 '{paper_title}' 的投稿项目"

    sub_file = matches[0]
    content = sub_file.read_text()

    stages = ["idea", "outline", "draft", "internal_review", "submit", "camera_ready", "published"]

    if stage:
        # Update frontmatter
        content = content.replace(
            f"stage: {_extract_field(content, 'stage')}",
            f"stage: {stage}"
        )
        # Update checklist
        stage_idx = stages.index(stage) if stage in stages else -1
        for i, s in enumerate(stages):
            marker = "x" if i <= stage_idx else " "
            # Find and update the corresponding checkbox
            stage_labels = {
                "idea": "💡 Idea",
                "outline": "📋 Outline",
                "draft": "📝 Draft",
                "internal_review": "🔍 Internal Review",
                "submit": "📤 Submit",
                "camera_ready": "📐 Camera Ready",
                "published": "🎉 Published",
            }
            label = stage_labels.get(s, "")
            if label:
                content = content.replace(f"- [ ] {label}", f"- [{marker}] {label}")
                content = content.replace(f"- [x] {label}", f"- [{marker}] {label}")

    if note:
        today = datetime.now().strftime("%Y-%m-%d")
        content += f"\n- [{today}] {note}\n"

    sub_file.write_text(content)
    return f"✅ 更新: {sub_file.stem} → stage={stage}" + (f" | note: {note[:50]}" if note else "")


def _extract_field(content: str, field: str) -> str:
    for line in content.split("\n")[:15]:
        if line.startswith(f"{field}:"):
            return line.split(":", 1)[1].strip()
    return ""


@mcp.tool()
def submission_dashboard() -> str:
    """Show all active submissions with their stages and deadlines."""
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    subs = list(SUBMISSIONS_DIR.glob("*.md"))

    if not subs:
        return "暂无投稿项目。使用 `create_submission` 创建。"

    output = "## 📤 Submission Dashboard\n\n"

    # Sort by deadline
    entries = []
    for f in subs:
        content = f.read_text()
        title = _extract_field(content, "title") or f.stem
        venue = _extract_field(content, "venue")
        deadline = _extract_field(content, "deadline")
        stage = _extract_field(content, "stage")
        entries.append({"title": title, "venue": venue, "deadline": deadline, "stage": stage})

    entries.sort(key=lambda x: x["deadline"] or "9999")

    stage_emoji = {
        "idea": "💡", "outline": "📋", "draft": "📝",
        "internal_review": "🔍", "submit": "📤",
        "camera_ready": "📐", "published": "🎉",
    }

    output += "| 论文 | 目标 | Deadline | 阶段 | 剩余 |\n"
    output += "|------|------|----------|------|------|\n"

    for e in entries:
        emoji = stage_emoji.get(e["stage"], "❓")
        days_left = ""
        if e["deadline"]:
            try:
                dl = datetime.strptime(e["deadline"], "%Y-%m-%d").date()
                d = (dl - datetime.now().date()).days
                if d < 0:
                    days_left = "⚠️ 已过期"
                elif d <= 7:
                    days_left = f"🔴 {d}天"
                elif d <= 30:
                    days_left = f"🟡 {d}天"
                else:
                    days_left = f"🟢 {d}天"
            except ValueError:
                days_left = "?"
        output += f"| {e['title'][:30]} | {e['venue']} | {e['deadline']} | {emoji} {e['stage']} | {days_left} |\n"

    return output


# ============================================================
# Feature: Knowledge Decay Alert — 知识衰减提醒
# ============================================================

KNOWLEDGE_TRACKER = Path(OBSIDIAN_VAULT) / "Research" / "knowledge-tracker.json"


@mcp.tool()
def knowledge_decay_check() -> str:
    """Check for important papers/concepts that need review based on spaced repetition.
    Papers with annotations are tracked; those not reviewed recently get flagged.
    Uses a simplified SM-2 algorithm for scheduling reviews.
    """
    # Load or initialize tracker
    if KNOWLEDGE_TRACKER.exists():
        tracker = json.loads(KNOWLEDGE_TRACKER.read_text())
    else:
        tracker = {"papers": {}, "last_scan": ""}

    # Scan for papers with annotations (only if last scan was >1 day ago)
    last_scan = tracker.get("last_scan", "")
    today = datetime.now().strftime("%Y-%m-%d")

    if last_scan != today:
        sql = """
        SELECT DISTINCT i.key,
               (SELECT value FROM itemData id2
                JOIN itemDataValues idv ON id2.valueID = idv.valueID
                JOIN fields f ON id2.fieldID = f.fieldID
                WHERE id2.itemID = i.itemID AND f.fieldName = 'title') as title,
               COUNT(ia.itemID) as annotation_count,
               MAX(ia.dateAdded) as last_annotated
        FROM items i
        JOIN itemAttachments att ON i.itemID = att.parentItemID
        JOIN itemAnnotations ia ON att.itemID = ia.parentItemID
        WHERE ia.text IS NOT NULL
        GROUP BY i.key
        HAVING annotation_count >= 3
        ORDER BY last_annotated DESC
        LIMIT 100
        """
        try:
            papers = _query_db(sql)
            for p in papers:
                key = p["key"]
                if key not in tracker["papers"]:
                    tracker["papers"][key] = {
                        "title": p.get("title", "Unknown"),
                        "annotations": p["annotation_count"],
                        "last_annotated": p["last_annotated"],
                        "last_reviewed": p["last_annotated"],
                        "interval_days": 7,
                        "ease_factor": 2.5,
                        "reviews": 0,
                    }
        except Exception:
            pass

        tracker["last_scan"] = today
        KNOWLEDGE_TRACKER.parent.mkdir(parents=True, exist_ok=True)
        KNOWLEDGE_TRACKER.write_text(json.dumps(tracker, indent=2, ensure_ascii=False))

    # Find papers due for review
    due_papers = []
    for key, info in tracker["papers"].items():
        last_reviewed = info.get("last_reviewed", "")
        interval = info.get("interval_days", 7)
        if last_reviewed:
            try:
                last_dt = datetime.strptime(last_reviewed[:10], "%Y-%m-%d")
                next_review = last_dt + timedelta(days=interval)
                if next_review.date() <= datetime.now().date():
                    days_overdue = (datetime.now().date() - next_review.date()).days
                    due_papers.append({
                        "key": key,
                        "title": info["title"],
                        "annotations": info["annotations"],
                        "days_overdue": days_overdue,
                        "interval": interval,
                    })
            except ValueError:
                continue

    if not due_papers:
        return "✅ 所有重要论文都在复习周期内，暂无需要回顾的内容。"

    due_papers.sort(key=lambda x: x["days_overdue"], reverse=True)

    output = "## 🧠 Knowledge Decay Alert\n\n"
    output += f"*{len(due_papers)} 篇重要论文需要回顾（基于间隔重复算法）：*\n\n"

    for i, p in enumerate(due_papers[:10], 1):
        urgency = "🔴" if p["days_overdue"] > 14 else "🟡" if p["days_overdue"] > 7 else "🟢"
        output += f"{i}. {urgency} **{p['title'][:60]}** (`{p['key']}`)\n"
        output += f"   {p['annotations']} 条批注 | 超期 {p['days_overdue']} 天 | 下次间隔 {p['interval']} 天\n\n"

    output += "---\n使用 `knowledge_review_done(paper_key, quality)` 标记已回顾。"
    return output


@mcp.tool()
def knowledge_review_done(paper_key: str, quality: int = 3) -> str:
    """Mark a paper as reviewed. Updates the spaced repetition schedule.
    quality: 1-5 (1=completely forgot, 3=recalled with effort, 5=perfect recall)
    """
    if not KNOWLEDGE_TRACKER.exists():
        return "❌ 知识追踪器未初始化。请先运行 `knowledge_decay_check()`。"

    tracker = json.loads(KNOWLEDGE_TRACKER.read_text())

    if paper_key not in tracker["papers"]:
        return f"❌ 论文 {paper_key} 不在追踪列表中。"

    info = tracker["papers"][paper_key]
    today = datetime.now().strftime("%Y-%m-%d")

    # SM-2 algorithm (simplified)
    ease = info.get("ease_factor", 2.5)
    interval = info.get("interval_days", 7)
    reviews = info.get("reviews", 0)

    if quality < 3:
        interval = 1
        reviews = 0
    else:
        ease = ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        ease = max(1.3, ease)
        if reviews == 0:
            interval = 1
        elif reviews == 1:
            interval = 6
        else:
            interval = int(interval * ease)

    info["last_reviewed"] = today
    info["interval_days"] = interval
    info["ease_factor"] = ease
    info["reviews"] = reviews + 1

    tracker["papers"][paper_key] = info
    KNOWLEDGE_TRACKER.write_text(json.dumps(tracker, indent=2, ensure_ascii=False))

    return f"✅ 已标记 `{paper_key}` 为已回顾 (质量={quality})\n下次回顾: {interval} 天后 ({(datetime.now() + timedelta(days=interval)).strftime('%Y-%m-%d')})"


# ============================================================
# Feature: Auto Knowledge Graph — 自动知识图谱
# ============================================================

KNOWLEDGE_GRAPH_PATH = Path(OBSIDIAN_VAULT) / "Research" / "knowledge-graph.json"


@mcp.tool()
def knowledge_graph_build(limit: int = 50) -> str:
    """Build/update the knowledge graph by extracting concepts from paper annotations.
    Extracts key concepts, methods, and their relationships from your Zotero annotations.
    """
    import re

    # Get annotated papers
    sql = """
    SELECT i.key,
           (SELECT value FROM itemData id2
            JOIN itemDataValues idv ON id2.valueID = idv.valueID
            JOIN fields f ON id2.fieldID = f.fieldID
            WHERE id2.itemID = i.itemID AND f.fieldName = 'title') as title,
           ia.text, ia.comment
    FROM items i
    JOIN itemAttachments att ON i.itemID = att.parentItemID
    JOIN itemAnnotations ia ON att.itemID = ia.parentItemID
    WHERE ia.text IS NOT NULL OR ia.comment IS NOT NULL
    ORDER BY ia.dateAdded DESC
    LIMIT ?
    """

    try:
        rows = _query_db(sql, (limit * 5,))
    except Exception as e:
        return f"❌ 数据库查询失败: {e}"

    if not rows:
        return "没有找到论文批注数据。"

    # Load existing graph
    if KNOWLEDGE_GRAPH_PATH.exists():
        graph = json.loads(KNOWLEDGE_GRAPH_PATH.read_text())
    else:
        graph = {"concepts": {}, "edges": [], "papers": {}, "updated": ""}

    # Define concept patterns
    concept_patterns = [
        r'\b(world model[s]?)\b',
        r'\b(reinforcement learning)\b',
        r'\b(transformer[s]?)\b',
        r'\b(attention mechanism[s]?)\b',
        r'\b(self-supervised learning)\b',
        r'\b(contrastive learning)\b',
        r'\b(diffusion model[s]?)\b',
        r'\b(language model[s]?)\b',
        r'\b(vision[- ]language)\b',
        r'\b(chain[- ]of[- ]thought)\b',
        r'\b(in[- ]context learning)\b',
        r'\b(few[- ]shot)\b',
        r'\b(zero[- ]shot)\b',
        r'\b(fine[- ]tun(?:e|ing))\b',
        r'\b(RLHF|PPO|DPO)\b',
        r'\b(retrieval[- ]augmented)\b',
        r'\b(multi[- ]?modal)\b',
        r'\b(embodied)\b',
        r'\b(planning)\b',
        r'\b(reasoning)\b',
        r'\b(representation learning)\b',
        r'\b(knowledge distillation)\b',
        r'\b(curriculum learning)\b',
        r'\b(meta[- ]learning)\b',
        r'\b(test[- ]time (?:training|adaptation|compute))\b',
        r'\b(concept[- ](?:learning|reasoning|grounding))\b',
        r'\b(VLM|MLLM)\b',
        r'\b(latent (?:space|reasoning|representation))\b',
        r'\b(self[- ]evolv(?:e|ing))\b',
    ]

    # Extract concepts from annotations
    paper_concepts: dict[str, set] = {}
    for row in rows:
        key = row["key"]
        text = ((row.get("text") or "") + " " + (row.get("comment") or "")).lower()

        if key not in paper_concepts:
            paper_concepts[key] = set()

        for pattern in concept_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                concept = m.lower().strip()
                paper_concepts[key].add(concept)

                if concept not in graph["concepts"]:
                    graph["concepts"][concept] = {"count": 0, "papers": []}
                graph["concepts"][concept]["count"] += 1
                if key not in graph["concepts"][concept]["papers"]:
                    graph["concepts"][concept]["papers"].append(key)

        if row.get("title"):
            graph["papers"][key] = row["title"]

    # Build edges (concepts co-occurring in the same paper)
    existing_edges = {(e["source"], e["target"]) for e in graph["edges"]}
    for key, concepts in paper_concepts.items():
        concept_list = list(concepts)
        for i in range(len(concept_list)):
            for j in range(i + 1, len(concept_list)):
                edge = tuple(sorted([concept_list[i], concept_list[j]]))
                if edge not in existing_edges:
                    graph["edges"].append({
                        "source": edge[0],
                        "target": edge[1],
                        "papers": [key],
                        "weight": 1,
                    })
                    existing_edges.add(edge)
                else:
                    for e in graph["edges"]:
                        if (e["source"], e["target"]) == edge or (e["target"], e["source"]) == edge:
                            e["weight"] = e.get("weight", 1) + 1
                            if key not in e.get("papers", []):
                                e.setdefault("papers", []).append(key)
                            break

    graph["updated"] = datetime.now().isoformat()
    KNOWLEDGE_GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_GRAPH_PATH.write_text(json.dumps(graph, indent=2, ensure_ascii=False))

    # Summary
    output = "## 🕸️ Knowledge Graph Updated\n\n"
    output += f"**概念节点**: {len(graph['concepts'])} | **关系边**: {len(graph['edges'])} | **论文**: {len(graph['papers'])}\n\n"

    # Top concepts
    top = sorted(graph["concepts"].items(), key=lambda x: x[1]["count"], reverse=True)[:15]
    output += "### Top 概念\n"
    output += "| 概念 | 出现次数 | 相关论文数 |\n|------|----------|------------|\n"
    for name, info in top:
        output += f"| {name} | {info['count']} | {len(info['papers'])} |\n"

    # Strongest connections
    strong_edges = sorted(graph["edges"], key=lambda x: x.get("weight", 1), reverse=True)[:10]
    output += "\n### 最强连接\n"
    for e in strong_edges:
        output += f"- **{e['source']}** ↔ **{e['target']}** (weight: {e.get('weight', 1)})\n"

    return output


@mcp.tool()
def knowledge_graph_query(concept: str) -> str:
    """Query the knowledge graph for a specific concept.
    Shows related concepts, papers, and connections.
    """
    if not KNOWLEDGE_GRAPH_PATH.exists():
        return "知识图谱尚未构建。请先运行 `knowledge_graph_build()`。"

    graph = json.loads(KNOWLEDGE_GRAPH_PATH.read_text())
    concept_lower = concept.lower()

    # Find concept
    if concept_lower not in graph["concepts"]:
        # Try partial match
        matches = [c for c in graph["concepts"] if concept_lower in c]
        if not matches:
            return f"未找到概念 '{concept}'。可用概念: {', '.join(list(graph['concepts'].keys())[:20])}"
        concept_lower = matches[0]

    info = graph["concepts"][concept_lower]

    output = f"## 🔍 Concept: {concept_lower}\n\n"
    output += f"**出现次数**: {info['count']} | **相关论文**: {len(info['papers'])}\n\n"

    # Related papers
    output += "### 📄 相关论文\n"
    for key in info["papers"][:10]:
        title = graph["papers"].get(key, key)
        output += f"- {title} (`{key}`)\n"

    # Connected concepts (via edges)
    connected = []
    for e in graph["edges"]:
        if e["source"] == concept_lower:
            connected.append((e["target"], e.get("weight", 1)))
        elif e["target"] == concept_lower:
            connected.append((e["source"], e.get("weight", 1)))

    connected.sort(key=lambda x: x[1], reverse=True)

    if connected:
        output += "\n### 🔗 关联概念\n"
        for name, weight in connected[:10]:
            bar = "█" * min(weight, 10)
            output += f"- {name} {bar} ({weight})\n"

    return output


@mcp.tool()
def knowledge_graph_gaps() -> str:
    """Identify potential knowledge gaps in your graph.
    Finds concepts with few connections or papers with isolated concepts.
    """
    if not KNOWLEDGE_GRAPH_PATH.exists():
        return "知识图谱尚未构建。请先运行 `knowledge_graph_build()`。"

    graph = json.loads(KNOWLEDGE_GRAPH_PATH.read_text())

    # Find isolated concepts (few connections)
    concept_connections: dict[str, int] = {c: 0 for c in graph["concepts"]}
    for e in graph["edges"]:
        concept_connections[e["source"]] = concept_connections.get(e["source"], 0) + e.get("weight", 1)
        concept_connections[e["target"]] = concept_connections.get(e["target"], 0) + e.get("weight", 1)

    isolated = [(c, conn) for c, conn in concept_connections.items() if conn <= 2 and graph["concepts"][c]["count"] >= 3]
    isolated.sort(key=lambda x: graph["concepts"][x[0]]["count"], reverse=True)

    output = "## 🔍 Knowledge Gaps\n\n"

    if isolated:
        output += "### 🏝️ 孤立概念（出现多次但缺少连接）\n"
        output += "*这些概念你关注过，但还没和其他概念建立联系：*\n\n"
        for concept, conn in isolated[:10]:
            info = graph["concepts"][concept]
            output += f"- **{concept}** — {info['count']}次出现, {conn}个连接\n"
        output += "\n"

    # Find pairs of concepts that should be connected but aren't
    high_count_concepts = [c for c, info in graph["concepts"].items() if info["count"] >= 5]
    existing_pairs = {(e["source"], e["target"]) for e in graph["edges"]}
    existing_pairs.update({(e["target"], e["source"]) for e in graph["edges"]})

    missing_links = []
    for i, c1 in enumerate(high_count_concepts):
        for c2 in high_count_concepts[i+1:]:
            if (c1, c2) not in existing_pairs:
                missing_links.append((c1, c2))

    if missing_links[:5]:
        output += "### ❓ 可能的缺失连接\n"
        output += "*这些高频概念之间还没有发现联系，值得探索：*\n\n"
        for c1, c2 in missing_links[:5]:
            output += f"- **{c1}** ↔ **{c2}** — 是否有联系？\n"

    if not isolated and not missing_links:
        output += "✅ 知识图谱连接良好，暂未发现明显 gap。"

    return output


if __name__ == "__main__":
    mcp.run()
