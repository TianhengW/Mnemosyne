# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27.0", "python-dotenv>=1.0.0"]
# ///

"""
独立定时推送脚本 — 由 macOS launchd 调度，不依赖 Claude Code。

用法:
  uv run scripts/daily-push.py --type morning    # 早间推送（论文 + deadline）
  uv run scripts/daily-push.py --type evening    # 晚间推送（工作摘要）
  uv run scripts/daily-push.py --type deadline   # 仅推送 deadline 提醒
  uv run scripts/daily-push.py --type resurface  # 知识回顾卡片
  uv run scripts/daily-push.py --type pulse      # 研究健康度周报
  uv run scripts/daily-push.py --type test       # 发送测试消息
"""

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
CONFIG_FILE = BASE_DIR / "config" / "notify.json"
DEADLINES_FILE = Path(os.path.expanduser("~/Documents/Obsidian Vault/Digital-Self/Goals/deadlines.json"))
WORKING_CONTEXT = Path(os.path.expanduser("~/Documents/Obsidian Vault/Digital-Self/Working/current-context.md"))
HF_DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"
SCREEN_MONITOR_DB = Path(os.path.expanduser("~/.cache/pa-screen-monitor/ocr.db"))
CHROME_HISTORY_DB = Path(os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/History"))

ACADEMIC_DOMAINS = [
    "arxiv.org", "scholar.google.com", "semanticscholar.org",
    "openreview.net", "paperswithcode.com", "huggingface.co/papers",
    "aclanthology.org", "proceedings.neurips.cc", "proceedings.mlr.press",
    "ieeexplore.ieee.org", "dl.acm.org",
]


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    print(f"[ERROR] 配置文件不存在: {CONFIG_FILE}")
    return {}


def send_serverchan(title: str, content: str) -> bool:
    sendkey = os.environ.get("SERVERCHAN_SENDKEY", "")
    if not sendkey:
        print("[ERROR] SendKey 未配置，请在 .env 文件中设置 SERVERCHAN_SENDKEY")
        return False

    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, data={"title": title[:32], "desp": content})
            result = resp.json()
            if result.get("code") == 0:
                print(f"[OK] 推送成功: {title}")
                return True
            else:
                print(f"[ERROR] 推送失败: {result.get('message', str(result))}")
                return False
    except Exception as e:
        print(f"[ERROR] 网络请求失败: {e}")
        return False


def fetch_daily_papers(topics: list[str]) -> str:
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.get(HF_DAILY_PAPERS_URL, params={"date": today})
            if resp.status_code != 200:
                return f"获取论文失败: HTTP {resp.status_code}"
            papers = resp.json()
    except Exception as e:
        return f"网络请求失败: {e}"

    if not papers:
        return "今日暂无新论文"

    relevant = []
    for paper in papers[:50]:
        paper_info = paper.get("paper", {})
        title = paper_info.get("title", "")
        summary = paper_info.get("summary", "")
        text = (title + " " + summary).lower()

        for topic in topics:
            if topic.lower() in text:
                authors = paper_info.get("authors", [])
                first_author = authors[0].get("name", "Unknown") if authors else "Unknown"
                relevant.append({
                    "title": title,
                    "authors": first_author,
                    "summary": summary[:120] + "..." if len(summary) > 120 else summary,
                    "topic": topic,
                })
                break

    content = f"## 📚 今日论文推荐 ({today})\n\n"

    if relevant:
        content += f"共 {len(relevant)} 篇与你研究相关：\n\n"
        for i, p in enumerate(relevant[:8], 1):
            content += f"### {i}. {p['title']}\n"
            content += f"**方向:** {p['topic']} | **作者:** {p['authors']}\n"
            content += f"> {p['summary']}\n\n"
    else:
        content += f"今日 {len(papers)} 篇热门论文中未匹配到你的研究方向。\n\n"
        content += "**热门 Top 5:**\n"
        for p in papers[:5]:
            pi = p.get("paper", {})
            content += f"- {pi.get('title', 'N/A')}\n"

    return content


def check_deadlines() -> str:
    if not DEADLINES_FILE.exists():
        return ""

    deadlines = json.loads(DEADLINES_FILE.read_text())
    today = datetime.now().date()

    urgent = []
    for d in deadlines:
        try:
            dl_date = datetime.strptime(d["deadline"], "%Y-%m-%d").date()
            days_left = (dl_date - today).days
            if 0 <= days_left <= 7:
                urgency = "🔴" if days_left <= 3 else "🟡"
                urgent.append((days_left, urgency, d))
        except (ValueError, KeyError):
            continue

    if not urgent:
        return ""

    urgent.sort(key=lambda x: x[0])
    content = "## ⚠️ Deadline 提醒\n\n"
    for days_left, emoji, d in urgent:
        if days_left == 0:
            content += f"{emoji} **{d['name']}** — **今天截止!**\n"
        else:
            content += f"{emoji} **{d['name']}** — 还剩 **{days_left} 天** ({d['deadline']})\n"

    return content


def get_git_summary() -> str:
    repos = [
        os.path.expanduser("~/Documents/Autolab/codes"),
    ]

    all_commits = []
    for repo in repos:
        if not Path(repo).exists():
            continue
        try:
            result = subprocess.run(
                ["git", "log", "--since=1 day ago", "--oneline", "--no-merges", "--all"],
                capture_output=True, text=True, cwd=repo, timeout=10
            )
            if result.stdout.strip():
                all_commits.append(f"**{Path(repo).name}:**\n```\n{result.stdout.strip()}\n```")
        except (subprocess.TimeoutExpired, Exception):
            continue

    if not all_commits:
        return ""

    return "## 💻 今日代码活动\n\n" + "\n\n".join(all_commits)


def get_working_context() -> str:
    if not WORKING_CONTEXT.exists():
        return ""

    content = WORKING_CONTEXT.read_text()
    lines = content.split("\n")

    goals = []
    in_goals = False
    for line in lines:
        if "本周目标" in line:
            in_goals = True
            continue
        if in_goals:
            if line.strip().startswith("- ["):
                goals.append(line.strip())
            elif line.strip().startswith("#"):
                break

    if not goals:
        return ""

    return "## 🎯 本周目标\n\n" + "\n".join(goals)


def get_screen_activity_summary() -> str:
    """Get today's screen activity summary from the screen monitor DB."""
    if not SCREEN_MONITOR_DB.exists():
        return ""

    today = datetime.now().strftime("%Y-%m-%d")
    try:
        conn = sqlite3.connect(str(SCREEN_MONITOR_DB))
        conn.row_factory = sqlite3.Row

        app_rows = conn.execute(
            "SELECT app_name, COUNT(*) * 30 as seconds FROM screen_log WHERE timestamp LIKE ? GROUP BY app_name ORDER BY seconds DESC",
            (f"{today}%",)
        ).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM screen_log WHERE timestamp LIKE ?",
            (f"{today}%",)
        ).fetchone()

        conn.close()
    except Exception:
        return ""

    total_records = total["cnt"] if total else 0
    if total_records == 0:
        return ""

    total_hours = total_records * 30 / 3600

    content = f"## 📺 今日屏幕活动\n\n"
    content += f"**总记录时间**: {total_hours:.1f} 小时\n\n"

    if app_rows:
        content += "| 应用 | 时间 |\n|------|------|\n"
        for row in app_rows[:8]:
            minutes = row["seconds"] / 60
            if minutes >= 1:
                content += f"| {row['app_name']} | {minutes:.0f} 分钟 |\n"

    return content


def get_browser_reading_summary() -> str:
    """Get today's academic browsing from Chrome history."""
    if not CHROME_HISTORY_DB.exists():
        return ""

    tmp_db = os.path.join(tempfile.gettempdir(), "pa-push-chrome-history")
    try:
        shutil.copy2(str(CHROME_HISTORY_DB), tmp_db)
    except Exception:
        return ""

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # Chrome epoch: microseconds since 1601-01-01
    chrome_epoch_offset = 11644473600
    today_chrome = int((today_start.timestamp() + chrome_epoch_offset) * 1_000_000)

    try:
        conn = sqlite3.connect(f"file:{tmp_db}?mode=ro", uri=True)
        rows = conn.execute(
            "SELECT url, title, visit_count FROM urls WHERE last_visit_time > ? ORDER BY last_visit_time DESC",
            (today_chrome,)
        ).fetchall()
        conn.close()
    except Exception:
        return ""

    academic_papers = []
    for url, title, visit_count in rows:
        if any(domain in url for domain in ACADEMIC_DOMAINS):
            if title and title not in [p[1] for p in academic_papers]:
                academic_papers.append((url, title))

    if not academic_papers:
        return ""

    content = f"## 📖 今日学术浏览\n\n"
    content += f"共浏览 {len(academic_papers)} 篇学术内容：\n\n"
    for url, title in academic_papers[:10]:
        short_title = title[:60] + "..." if len(title) > 60 else title
        content += f"- {short_title}\n"

    return content


def push_morning():
    config = load_config()
    topics = config.get("topics", [])

    parts = []

    papers_content = fetch_daily_papers(topics)
    parts.append(papers_content)

    deadline_content = check_deadlines()
    if deadline_content:
        parts.append(deadline_content)

    content = "\n\n---\n\n".join(parts)
    content += "\n\n---\n*来自你的科研助手 PA · 早间推送*"

    title = "🌅 早间科研速递"
    send_serverchan(title, content)


def push_evening():
    parts = []

    screen_content = get_screen_activity_summary()
    if screen_content:
        parts.append(screen_content)

    browser_content = get_browser_reading_summary()
    if browser_content:
        parts.append(browser_content)

    git_content = get_git_summary()
    if git_content:
        parts.append(git_content)

    context_content = get_working_context()
    if context_content:
        parts.append(context_content)

    if not parts:
        content = "今天没有检测到活动记录。\n\n早点休息 🌙"
    else:
        content = "\n\n---\n\n".join(parts)

    content += "\n\n---\n*来自你的科研助手 PA · 晚间总结*"

    title = "🌙 今日工作回顾"
    send_serverchan(title, content)


def push_deadline_only():
    content = check_deadlines()
    if not content:
        print("[INFO] 近 7 天无紧急 deadline，跳过推送")
        return

    content += "\n\n---\n*来自你的科研助手 PA*"
    title = "⚠️ Deadline 提醒"
    send_serverchan(title, content)


def push_test():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"## 🧪 测试推送\n\n推送时间: {now}\n\n如果你看到这条消息，说明 Server酱 配置正确！\n\n---\n*来自你的科研助手 PA*"
    title = "🧪 PA 推送测试"
    send_serverchan(title, content)


def push_resurface():
    """知识回顾 — 从 Zotero 批注中随机拉取 2-8 周前的 insight"""
    import random

    zotero_db = os.path.expanduser("~/Zotero/zotero.sqlite")
    if not Path(zotero_db).exists():
        print("[ERROR] Zotero 数据库不存在")
        return

    # Copy DB to avoid lock
    tmp_db = os.path.join(tempfile.gettempdir(), "pa-push-zotero.sqlite")
    shutil.copy2(zotero_db, tmp_db)

    date_min = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    date_max = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")

    conn = sqlite3.connect(f"file:{tmp_db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    sql = """
    SELECT ia.text, ia.comment, ia.dateAdded,
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
    LIMIT 10
    """
    rows = conn.execute(sql, (date_min, date_max)).fetchall()
    conn.close()

    if not rows:
        print("[INFO] 2-8 周前没有批注记录，跳过")
        return

    selected = random.sample(list(rows), min(3, len(rows)))

    content = "## 🔄 知识回顾卡片\n\n*这些是你 2-8 周前读过的内容，试着和当前工作建立联系。*\n\n"
    for i, r in enumerate(selected, 1):
        content += f"### 卡片 {i} — {r['paper_title'] or '未知论文'}\n"
        if r["text"]:
            content += f"> {r['text'][:200]}\n"
        if r["comment"]:
            content += f"\n📝 你的批注: {r['comment'][:150]}\n"
        content += "\n"

    content += "---\n**反思**: 这些旧知识对你现在在想的问题有什么启发？\n\n---\n*来自你的科研助手 PA · 知识回顾*"
    title = "🔄 知识回顾"
    send_serverchan(title, content)


def push_pulse():
    """研究健康度周报 — 聚合本周的各项研究活动数据"""
    today = datetime.now().date()
    week_start = today - timedelta(days=7)

    # Papers added this week
    papers_count = 0
    annotations_count = 0
    zotero_db = os.path.expanduser("~/Zotero/zotero.sqlite")
    if Path(zotero_db).exists():
        tmp_db = os.path.join(tempfile.gettempdir(), "pa-pulse-zotero.sqlite")
        shutil.copy2(zotero_db, tmp_db)
        conn = sqlite3.connect(f"file:{tmp_db}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM items WHERE itemTypeID IN (SELECT itemTypeID FROM itemTypes WHERE typeName IN ('journalArticle','conferencePaper','preprint')) AND DATE(dateAdded) BETWEEN ? AND ?",
                (week_start.isoformat(), today.isoformat())
            ).fetchone()
            papers_count = row[0] if row else 0

            row2 = conn.execute(
                "SELECT COUNT(*) FROM itemAnnotations WHERE DATE(dateAdded) BETWEEN ? AND ?",
                (week_start.isoformat(), today.isoformat())
            ).fetchone()
            annotations_count = row2[0] if row2 else 0
        finally:
            conn.close()

    # Git commits
    commits_count = 0
    repos = [os.path.expanduser("~/Documents/Autolab/codes")]
    for repo in repos:
        if Path(repo).exists():
            try:
                result = subprocess.run(
                    ["git", "log", f"--since={week_start}", "--oneline", "--no-merges", "--all"],
                    capture_output=True, text=True, cwd=repo, timeout=10
                )
                if result.stdout.strip():
                    commits_count += len(result.stdout.strip().split("\n"))
            except Exception:
                pass

    content = f"## 📈 Research Pulse — 本周回顾\n\n"
    content += f"| 指标 | 本周 |\n|------|------|\n"
    content += f"| 📄 新增论文 | {papers_count} |\n"
    content += f"| 📝 新增批注 | {annotations_count} |\n"
    content += f"| 💻 代码提交 | {commits_count} |\n"

    # Alerts
    if papers_count == 0 and annotations_count == 0:
        content += "\n⚠️ 本周没有阅读活动，是否需要调整计划？\n"
    if commits_count == 0:
        content += "\n⚠️ 本周没有代码提交。\n"

    content += "\n---\n*来自你的科研助手 PA · 周日晚报*"
    title = "📈 本周研究脉搏"
    send_serverchan(title, content)


def main():
    parser = argparse.ArgumentParser(description="PA 定时推送脚本")
    parser.add_argument(
        "--type",
        choices=["morning", "evening", "deadline", "resurface", "pulse", "test"],
        required=True,
        help="推送类型: morning(早间), evening(晚间), deadline(仅deadline), resurface(知识回顾), pulse(研究脉搏), test(测试)",
    )
    args = parser.parse_args()

    handlers = {
        "morning": push_morning,
        "evening": push_evening,
        "deadline": push_deadline_only,
        "resurface": push_resurface,
        "pulse": push_pulse,
        "test": push_test,
    }

    handlers[args.type]()


if __name__ == "__main__":
    main()
