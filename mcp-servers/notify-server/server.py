# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]>=1.0.0", "httpx>=0.27.0", "python-dotenv>=1.0.0"]
# ///

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

mcp = FastMCP("notify")

CONFIG_FILE = os.environ.get(
    "NOTIFY_CONFIG",
    os.path.expanduser("~/Documents/Autolab/codes/PA/config/notify.json"),
)

DEADLINES_FILE = os.environ.get(
    "DEADLINES_FILE",
    os.path.expanduser("~/Documents/Obsidian Vault/Digital-Self/Goals/deadlines.json"),
)

HF_DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"


def _load_config() -> dict:
    path = Path(CONFIG_FILE)
    if path.exists():
        return json.loads(path.read_text())
    return {"enabled_types": {}, "topics": [], "push_schedule": {}}


def _save_config(config: dict):
    path = Path(CONFIG_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False))


def _send_serverchan(title: str, content: str) -> dict:
    sendkey = os.environ.get("SERVERCHAN_SENDKEY", "")
    if not sendkey:
        return {"error": "SendKey 未配置。请在 .env 文件中设置 SERVERCHAN_SENDKEY"}

    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, data={"title": title[:32], "desp": content})
        return resp.json()


def _load_deadlines() -> list[dict]:
    path = Path(DEADLINES_FILE)
    if path.exists():
        return json.loads(path.read_text())
    return []


@mcp.tool()
def send_wechat(title: str, content: str) -> str:
    """Send a message to WeChat via Server酱.
    Title: max 32 chars. Content: supports Markdown.
    """
    result = _send_serverchan(title, content)
    if "error" in result:
        return f"❌ 推送失败: {result['error']}"
    if result.get("code") == 0:
        return f"✅ 推送成功: {title}"
    return f"❌ 推送失败: {result.get('message', str(result))}"


@mcp.tool()
def push_daily_papers() -> str:
    """Fetch today's papers from HuggingFace Daily Papers and push a summary to WeChat.
    Filters papers by configured research topics.
    """
    config = _load_config()
    topics = config.get("topics", [])

    today = datetime.now().strftime("%Y-%m-%d")

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.get(HF_DAILY_PAPERS_URL, params={"date": today})
            if resp.status_code != 200:
                return f"❌ 获取 HuggingFace 论文失败: HTTP {resp.status_code}"
            papers = resp.json()
    except Exception as e:
        return f"❌ 网络请求失败: {e}"

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
                relevant.append({
                    "title": title,
                    "authors": paper_info.get("authors", [{}])[0].get("name", "Unknown") if paper_info.get("authors") else "Unknown",
                    "summary": summary[:150] + "..." if len(summary) > 150 else summary,
                    "topic": topic,
                    "arxiv_id": paper_info.get("id", ""),
                })
                break

    if not relevant:
        msg_content = f"今日 HuggingFace 热门论文共 {len(papers)} 篇，但没有匹配你关注方向的论文。\n\n"
        msg_content += "**今日热门 Top 5:**\n"
        for p in papers[:5]:
            pi = p.get("paper", {})
            msg_content += f"- {pi.get('title', 'N/A')}\n"
    else:
        msg_content = f"## 📚 今日论文推荐 ({today})\n\n"
        msg_content += f"共找到 {len(relevant)} 篇相关论文：\n\n"
        for i, p in enumerate(relevant[:10], 1):
            msg_content += f"### {i}. {p['title']}\n"
            msg_content += f"**方向:** {p['topic']} | **作者:** {p['authors']}\n"
            msg_content += f"> {p['summary']}\n\n"

    msg_content += "\n---\n*来自你的科研助手 PA*"
    title = f"📚 今日论文 ({len(relevant)} 篇相关)" if relevant else "📚 今日论文速览"

    result = _send_serverchan(title, msg_content)
    if "error" in result:
        return f"❌ 推送失败: {result['error']}"
    if result.get("code") == 0:
        return f"✅ 论文推送成功: {len(relevant)} 篇相关论文已发送到微信"
    return f"❌ 推送失败: {result.get('message', str(result))}"


@mcp.tool()
def push_deadline_alert() -> str:
    """Check upcoming deadlines (within 7 days) and push alerts to WeChat."""
    deadlines = _load_deadlines()
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
        return "✅ 近 7 天无紧急 deadline"

    urgent.sort(key=lambda x: x[0])

    content = "## ⚠️ Deadline 提醒\n\n"
    for days_left, emoji, d in urgent:
        if days_left == 0:
            content += f"{emoji} **{d['name']}** — **今天截止!**\n"
        else:
            content += f"{emoji} **{d['name']}** — 还剩 **{days_left} 天** ({d['deadline']})\n"

    content += "\n---\n*来自你的科研助手 PA*"

    title = f"⚠️ {len(urgent)} 个 Deadline 临近"
    result = _send_serverchan(title, content)
    if "error" in result:
        return f"❌ 推送失败: {result['error']}"
    if result.get("code") == 0:
        return f"✅ Deadline 提醒已推送: {len(urgent)} 个临近截止"
    return f"❌ 推送失败: {result.get('message', str(result))}"


@mcp.tool()
def push_work_summary(summary: str) -> str:
    """Push a work completion or progress summary to WeChat.
    Use this after finishing a training run, experiment, or major task.
    """
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = f"## 📋 工作进度 ({today})\n\n{summary}\n\n---\n*来自你的科研助手 PA*"
    title = "📋 工作完成通知"

    result = _send_serverchan(title, content)
    if "error" in result:
        return f"❌ 推送失败: {result['error']}"
    if result.get("code") == 0:
        return "✅ 工作总结已推送到微信"
    return f"❌ 推送失败: {result.get('message', str(result))}"


@mcp.tool()
def get_push_config() -> str:
    """View current push notification configuration."""
    config = _load_config()
    has_key = "✅ 已配置" if config.get("serverchan_sendkey") else "❌ 未配置"

    output = "## 推送配置\n\n"
    output += f"**Server酱 SendKey:** {has_key}\n\n"
    output += "**推送时间:**\n"
    for name, time in config.get("push_schedule", {}).items():
        output += f"- {name}: {time}\n"
    output += "\n**启用的推送类型:**\n"
    for name, enabled in config.get("enabled_types", {}).items():
        status = "✅" if enabled else "❌"
        output += f"- {status} {name}\n"
    output += "\n**追踪方向:**\n"
    for topic in config.get("topics", []):
        output += f"- {topic}\n"

    return output


@mcp.tool()
def update_push_config(key: str, value: str) -> str:
    """Update push configuration.
    Supported keys: serverchan_sendkey, push_schedule.*, enabled_types.*
    Examples:
      key="serverchan_sendkey", value="SCT..."
      key="enabled_types.daily_papers", value="false"
      key="push_schedule.morning_papers", value="09:00"
    """
    config = _load_config()

    parts = key.split(".")
    if len(parts) == 1:
        config[parts[0]] = value
    elif len(parts) == 2:
        if parts[0] not in config:
            config[parts[0]] = {}
        if value.lower() in ("true", "false"):
            config[parts[0]][parts[1]] = value.lower() == "true"
        else:
            config[parts[0]][parts[1]] = value
    else:
        return f"❌ 不支持的配置路径: {key}"

    _save_config(config)
    return f"✅ 已更新: {key} = {value}"


if __name__ == "__main__":
    mcp.run()
