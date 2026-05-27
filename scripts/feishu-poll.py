# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27.0", "python-dotenv>=1.0.0"]
# ///

"""
飞书会议纪要轮询脚本 — 由 launchd 定期运行。

检查是否有新的飞书会议纪要文档，如有则下载并结构化保存到 Obsidian。

用法:
  uv run scripts/feishu-poll.py              # 拉取最近的会议纪要
  uv run scripts/feishu-poll.py --test       # 测试飞书 API 连接
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
CONFIG_FILE = BASE_DIR / "config" / "feishu.json"
NOTIFY_CONFIG = BASE_DIR / "config" / "notify.json"
MEETINGS_DIR = Path(os.path.expanduser("~/Documents/Obsidian Vault/Research/Meetings"))
STATE_FILE = BASE_DIR / "config" / ".feishu-poll-state.json"
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    print("[ERROR] 飞书配置文件不存在")
    return {}


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_poll": "", "processed_docs": []}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def get_tenant_token() -> str:
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        raise Exception("请在 .env 中设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
    url = f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
    with httpx.Client(timeout=15) as client:
        resp = client.post(url, json={
            "app_id": app_id,
            "app_secret": app_secret,
        })
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"获取 token 失败: {data.get('msg')}")
        return data["tenant_access_token"]


def send_wechat_notification(title: str, content: str):
    """Send notification via Server酱"""
    sendkey = os.environ.get("SERVERCHAN_SENDKEY", "")
    if not sendkey:
        return

    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    try:
        with httpx.Client(timeout=15) as client:
            client.post(url, data={"title": title[:32], "desp": content})
    except Exception:
        pass


def fetch_recent_docs(token: str) -> list[dict]:
    """Fetch recent documents from Feishu that might be meeting minutes."""
    # Search for documents with meeting-related keywords
    url = f"{FEISHU_API_BASE}/suite/docs-api/search/object"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "search_key": "会议",
        "count": 10,
        "offset": 0,
        "owner_ids": [],
        "docs_types": [8],  # docx type
    }

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, headers=headers, json=params)
            data = resp.json()
            if data.get("code") != 0:
                print(f"[WARN] 搜索文档失败: {data.get('msg')}")
                return []
            return data.get("data", {}).get("docs_entities", [])
    except Exception as e:
        print(f"[ERROR] 搜索请求失败: {e}")
        return []


def fetch_doc_content(token: str, doc_token: str) -> str:
    """Fetch raw content of a Feishu document."""
    url = f"{FEISHU_API_BASE}/docx/v1/documents/{doc_token}/raw_content"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=headers)
            data = resp.json()
            if data.get("code") != 0:
                return ""
            return data.get("data", {}).get("content", "")
    except Exception:
        return ""


def structure_meeting_notes(content: str, title: str) -> str:
    """Structure raw meeting content into markdown format."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Extract action items
    action_items = []
    for line in content.split("\n"):
        line_s = line.strip()
        if any(kw in line_s for kw in ["待办", "TODO", "需要", "负责", "跟进"]):
            action_items.append(line_s)

    # Extract decisions
    decisions = []
    for line in content.split("\n"):
        line_s = line.strip()
        if any(kw in line_s for kw in ["决定", "确定", "结论", "共识"]):
            decisions.append(line_s)

    structured = f"""---
date: {today}
source: feishu-auto
status: active
---

# Meeting: {title} — {today}

## 讨论内容

{content}

## Action Items
"""
    if action_items:
        for item in action_items:
            structured += f"- [ ] {item}\n"
    else:
        structured += "- [ ] [请手动补充]\n"

    structured += "\n## 决策\n"
    for d in decisions:
        structured += f"- {d}\n"

    return structured


def poll():
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        print("[ERROR] 飞书 App ID/Secret 未配置，请在 .env 中设置")
        return

    state = load_state()
    processed = set(state.get("processed_docs", []))

    try:
        token = get_tenant_token()
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    docs = fetch_recent_docs(token)
    new_meetings = []

    for doc in docs:
        doc_token = doc.get("docs_token", "")
        if not doc_token or doc_token in processed:
            continue

        title = doc.get("title", "未命名会议")
        content = fetch_doc_content(token, doc_token)
        if not content:
            continue

        # Save structured meeting note
        MEETINGS_DIR.mkdir(parents=True, exist_ok=True)
        structured = structure_meeting_notes(content, title)
        today = datetime.now().strftime("%Y-%m-%d")
        safe_title = re.sub(r'[^\w\s-]', '', title)[:30].strip()
        filename = f"{today}-{safe_title}.md"
        (MEETINGS_DIR / filename).write_text(structured)

        processed.add(doc_token)
        new_meetings.append(title)
        print(f"[OK] 保存会议纪要: {filename}")

    # Update state
    state["last_poll"] = datetime.now().isoformat()
    state["processed_docs"] = list(processed)
    save_state(state)

    # Send notification if new meetings found
    if new_meetings and config.get("notify_on_new", True):
        notify_content = "## 📅 新会议纪要\n\n"
        for t in new_meetings:
            notify_content += f"- {t}\n"
        notify_content += "\n已自动结构化保存到 Obsidian。"
        send_wechat_notification("📅 新会议纪要已整理", notify_content)

    if not new_meetings:
        print("[INFO] 没有新的会议纪要")


def test_connection():
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        print("[ERROR] 请在 .env 中设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        return

    try:
        token = get_tenant_token()
        print(f"[OK] 飞书 API 连接成功 (token: {token[:10]}...)")
    except Exception as e:
        print(f"[ERROR] 连接失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="飞书会议纪要轮询")
    parser.add_argument("--test", action="store_true", help="测试飞书 API 连接")
    args = parser.parse_args()

    if args.test:
        test_connection()
    else:
        poll()


if __name__ == "__main__":
    main()
