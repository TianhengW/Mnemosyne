# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]>=1.0.0", "httpx>=0.27.0", "python-dotenv>=1.0.0"]
# ///

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

mcp = FastMCP("feishu")

CONFIG_FILE = os.environ.get(
    "FEISHU_CONFIG",
    os.path.expanduser("~/Documents/Autolab/codes/PA/config/feishu.json"),
)
OBSIDIAN_VAULT = os.environ.get("OBSIDIAN_VAULT", os.path.expanduser("~/Documents/Obsidian Vault"))
MEETINGS_DIR = Path(OBSIDIAN_VAULT) / "Research" / "Meetings"

FEISHU_API_BASE = "https://open.feishu.cn/open-apis"


def _load_config() -> dict:
    path = Path(CONFIG_FILE)
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _get_tenant_token() -> str:
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        raise ValueError("飞书 App ID 或 Secret 未配置。请在 .env 文件中设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")

    url = f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
    with httpx.Client(timeout=15) as client:
        resp = client.post(url, json={"app_id": app_id, "app_secret": app_secret})
        data = resp.json()
        if data.get("code") != 0:
            raise ValueError(f"获取 token 失败: {data.get('msg')}")
        return data["tenant_access_token"]


def _ensure_meetings_dir():
    MEETINGS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Meeting Notes Management
# ============================================================

@mcp.tool()
def process_meeting_notes(content: str, title: str = "", participants: str = "") -> str:
    """Process raw meeting notes (from Feishu or manual input) into structured format.
    Extracts action items, key decisions, and discussion points.
    Saves to Obsidian Research/Meetings/ directory.

    Args:
        content: Raw meeting notes text (paste from Feishu 智能纪要)
        title: Meeting title (optional, will auto-generate if empty)
        participants: Comma-separated participant names
    """
    _ensure_meetings_dir()
    today = datetime.now().strftime("%Y-%m-%d")
    time_now = datetime.now().strftime("%H:%M")

    if not title:
        first_line = content.strip().split("\n")[0][:50]
        title = first_line if first_line else f"Meeting-{today}"

    # Extract action items (lines with TODO, 待办, action, 需要, 负责)
    action_patterns = [
        r'(?:TODO|待办|action|需要|负责|跟进|确认)[：:\s]*(.+)',
        r'[-•]\s*\[[ ]\]\s*(.+)',
        r'(\S+)\s*(?:负责|跟进|确认)\s*(.+)',
    ]
    action_items = []
    for line in content.split("\n"):
        line_stripped = line.strip()
        for pattern in action_patterns:
            match = re.search(pattern, line_stripped, re.IGNORECASE)
            if match:
                action_items.append(line_stripped)
                break

    # Extract decisions (lines with 决定, 确定, 决策, agreed)
    decisions = []
    for line in content.split("\n"):
        line_stripped = line.strip()
        if any(kw in line_stripped for kw in ["决定", "确定", "决策", "agreed", "结论", "共识"]):
            decisions.append(line_stripped)

    # Build structured note
    meeting_id = f"MTG-{today.replace('-', '')}-{time_now.replace(':', '')}"

    structured = f"""---
meeting_id: {meeting_id}
date: {today}
participants: [{participants}]
source: feishu
status: active
---

# Meeting: {title} — {today}

## 基本信息
- 时间: {today} {time_now}
- 参与者: {participants or '待补充'}
- 来源: 飞书智能纪要

## 讨论要点

{content}

## Action Items
"""

    if action_items:
        for item in action_items:
            structured += f"- [ ] {item}\n"
    else:
        structured += "- [ ] [请手动添加 action items]\n"

    structured += "\n## 决策记录\n"
    if decisions:
        for d in decisions:
            structured += f"- {d}\n"
    else:
        structured += "- [无明确决策记录]\n"

    structured += f"""
## Follow-up
- 下次会议时间: [待定]
- 需要准备的材料: [待补充]
"""

    # Save to Obsidian
    safe_title = re.sub(r'[^\w\s-]', '', title)[:40].strip()
    filename = f"{today}-{safe_title}.md"
    file_path = MEETINGS_DIR / filename
    file_path.write_text(structured)

    return f"✅ 会议纪要已结构化保存: Research/Meetings/{filename}\n\n提取到 {len(action_items)} 个 Action Items, {len(decisions)} 个决策记录。"


@mcp.tool()
def list_meetings(days: int = 30) -> str:
    """List recent meeting notes from Obsidian."""
    _ensure_meetings_dir()
    cutoff = datetime.now() - timedelta(days=days)

    meetings = []
    for f in sorted(MEETINGS_DIR.glob("*.md"), reverse=True):
        try:
            date_str = f.stem[:10]
            meeting_date = datetime.strptime(date_str, "%Y-%m-%d")
            if meeting_date >= cutoff:
                content = f.read_text()
                # Extract title
                title = f.stem[11:] if len(f.stem) > 10 else f.stem
                # Count pending action items
                pending = content.count("- [ ]")
                done = content.count("- [x]")
                meetings.append((date_str, title, pending, done))
        except (ValueError, IndexError):
            continue

    if not meetings:
        return f"最近 {days} 天没有会议记录。"

    output = "## 📅 近期会议\n\n"
    output += "| 日期 | 标题 | 待办 | 已完成 |\n|------|------|------|--------|\n"
    for date, title, pending, done in meetings:
        output += f"| {date} | {title} | {pending} | {done} |\n"

    return output


@mcp.tool()
def get_meeting(filename: str) -> str:
    """Get full content of a specific meeting note.
    Use list_meetings() first to find the filename.
    """
    _ensure_meetings_dir()
    file_path = MEETINGS_DIR / filename
    if not file_path.exists():
        # Try fuzzy match
        matches = list(MEETINGS_DIR.glob(f"*{filename}*"))
        if matches:
            file_path = matches[0]
        else:
            return f"❌ 未找到会议记录: {filename}"

    return file_path.read_text()


@mcp.tool()
def check_action_items(status: str = "pending") -> str:
    """Check action items across all meetings.
    Status: pending (unchecked), done (checked), overdue (pending + >7 days old), all.
    """
    _ensure_meetings_dir()
    today = datetime.now().date()
    items = []

    for f in sorted(MEETINGS_DIR.glob("*.md"), reverse=True):
        try:
            date_str = f.stem[:10]
            meeting_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        content = f.read_text()
        in_actions = False
        for line in content.split("\n"):
            if "Action Items" in line:
                in_actions = True
                continue
            if in_actions and line.startswith("#"):
                break
            if in_actions:
                if "- [ ]" in line:
                    days_old = (today - meeting_date).days
                    items.append({
                        "text": line.replace("- [ ]", "").strip(),
                        "meeting": f.stem,
                        "date": date_str,
                        "days_old": days_old,
                        "done": False,
                    })
                elif "- [x]" in line:
                    items.append({
                        "text": line.replace("- [x]", "").strip(),
                        "meeting": f.stem,
                        "date": date_str,
                        "days_old": 0,
                        "done": True,
                    })

    # Filter by status
    if status == "pending":
        items = [i for i in items if not i["done"]]
    elif status == "done":
        items = [i for i in items if i["done"]]
    elif status == "overdue":
        items = [i for i in items if not i["done"] and i["days_old"] > 7]

    if not items:
        return f"没有 {status} 状态的 action items。"

    output = f"## Action Items ({status})\n\n"
    for item in items:
        emoji = "✅" if item["done"] else ("🔴" if item["days_old"] > 7 else "⬜")
        age = f" ({item['days_old']}天前)" if not item["done"] else ""
        output += f"{emoji} {item['text']}{age}\n  └─ from: {item['meeting']}\n\n"

    return output


@mcp.tool()
def complete_action_item(meeting_filename: str, item_text: str) -> str:
    """Mark an action item as completed in a meeting note.
    Provide the meeting filename and the text of the action item to complete.
    """
    _ensure_meetings_dir()
    file_path = MEETINGS_DIR / meeting_filename
    if not file_path.exists():
        matches = list(MEETINGS_DIR.glob(f"*{meeting_filename}*"))
        if matches:
            file_path = matches[0]
        else:
            return f"❌ 未找到: {meeting_filename}"

    content = file_path.read_text()
    # Find and replace the action item
    target = f"- [ ] {item_text}"
    if target not in content:
        # Try fuzzy match
        for line in content.split("\n"):
            if "- [ ]" in line and item_text[:20] in line:
                target = line
                break
        else:
            return f"❌ 未找到 action item: {item_text[:50]}"

    new_content = content.replace(target, target.replace("- [ ]", "- [x]"), 1)
    file_path.write_text(new_content)
    return f"✅ 已完成: {item_text[:50]}"


# ============================================================
# Feishu API Integration
# ============================================================

@mcp.tool()
def fetch_feishu_doc(doc_url: str) -> str:
    """Fetch content from a Feishu document URL.
    Requires feishu.json to be configured with app_id and app_secret.
    The app needs docx:document:readonly permission.
    """
    # Extract document token from URL
    match = re.search(r'/docx/([a-zA-Z0-9]+)', doc_url)
    if not match:
        return "❌ 无法从 URL 中提取文档 token。请确保是飞书文档链接。"

    doc_token = match.group(1)

    try:
        token = _get_tenant_token()
    except ValueError as e:
        return f"❌ {e}"

    # Fetch document content
    url = f"{FEISHU_API_BASE}/docx/v1/documents/{doc_token}/raw_content"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=headers)
            data = resp.json()

        if data.get("code") != 0:
            return f"❌ 获取文档失败: {data.get('msg', str(data))}"

        content = data.get("data", {}).get("content", "")
        return content if content else "文档内容为空"

    except Exception as e:
        return f"❌ 请求失败: {e}"


@mcp.tool()
def get_feishu_config() -> str:
    """View current Feishu integration configuration."""
    config = _load_config()
    has_id = "✅" if config.get("app_id") else "❌"
    has_secret = "✅" if config.get("app_secret") else "❌"

    output = "## 飞书集成配置\n\n"
    output += f"**App ID:** {has_id} {'已配置' if config.get('app_id') else '未配置'}\n"
    output += f"**App Secret:** {has_secret} {'已配置' if config.get('app_secret') else '未配置'}\n"
    output += f"\n配置文件: `config/feishu.json`\n"
    output += "\n### 设置步骤\n"
    output += "1. 访问 https://open.feishu.cn/app 创建应用\n"
    output += "2. 添加权限: `docx:document:readonly`\n"
    output += "3. 将 App ID 和 App Secret 填入 config/feishu.json\n"
    return output


if __name__ == "__main__":
    mcp.run()
