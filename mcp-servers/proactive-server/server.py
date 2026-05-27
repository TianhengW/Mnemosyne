# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]>=1.0.0", "httpx>=0.27.0"]
# ///

import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("proactive")

DEADLINES_FILE = os.environ.get(
    "DEADLINES_FILE",
    os.path.expanduser("~/Documents/Obsidian Vault/Digital-Self/Goals/deadlines.json"),
)

# Major ML/AI conference deadlines (updated regularly)
DEFAULT_CONFERENCES = [
    {"name": "NeurIPS 2026", "deadline": "2026-05-22", "venue": "NeurIPS", "type": "main"},
    {"name": "ICML 2027", "deadline": "2027-01-23", "venue": "ICML", "type": "main"},
    {"name": "ICLR 2027", "deadline": "2026-10-01", "venue": "ICLR", "type": "main"},
    {"name": "CVPR 2027", "deadline": "2026-11-15", "venue": "CVPR", "type": "main"},
    {"name": "ACL 2027", "deadline": "2027-02-15", "venue": "ACL", "type": "main"},
    {"name": "AAAI 2027", "deadline": "2026-08-15", "venue": "AAAI", "type": "main"},
    {"name": "ECCV 2026", "deadline": "2026-03-07", "venue": "ECCV", "type": "main"},
    {"name": "CoRL 2026", "deadline": "2026-06-20", "venue": "CoRL", "type": "main"},
    {"name": "NeurIPS Workshop", "deadline": "2026-09-15", "venue": "NeurIPS-W", "type": "workshop"},
    {"name": "ICML Workshop", "deadline": "2026-05-10", "venue": "ICML-W", "type": "workshop"},
]


def _load_deadlines() -> list[dict]:
    path = Path(DEADLINES_FILE)
    if path.exists():
        return json.loads(path.read_text())
    return DEFAULT_CONFERENCES


def _save_deadlines(deadlines: list[dict]):
    path = Path(DEADLINES_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(deadlines, indent=2, ensure_ascii=False))


@mcp.tool()
def check_deadlines(days_ahead: int = 90) -> str:
    """Check upcoming conference deadlines within the next N days."""
    deadlines = _load_deadlines()
    today = datetime.now().date()
    cutoff = today + timedelta(days=days_ahead)

    upcoming = []
    for d in deadlines:
        try:
            dl_date = datetime.strptime(d["deadline"], "%Y-%m-%d").date()
        except ValueError:
            continue
        if today <= dl_date <= cutoff:
            days_left = (dl_date - today).days
            urgency = "🔴" if days_left <= 14 else "🟡" if days_left <= 30 else "🟢"
            upcoming.append((days_left, urgency, d))

    upcoming.sort(key=lambda x: x[0])

    if not upcoming:
        return f"No deadlines in the next {days_ahead} days."

    output = ["## Upcoming Deadlines\n"]
    for days_left, urgency, d in upcoming:
        output.append(
            f"{urgency} **{d['name']}** — {d['deadline']} ({days_left} days left) [{d['type']}]"
        )

    return "\n".join(output)


@mcp.tool()
def add_deadline(name: str, deadline: str, venue: str = "", type: str = "custom") -> str:
    """Add a custom deadline (e.g., paper submission, presentation, milestone).
    Date format: YYYY-MM-DD.
    """
    deadlines = _load_deadlines()
    deadlines.append({"name": name, "deadline": deadline, "venue": venue, "type": type})
    _save_deadlines(deadlines)
    return f"Added deadline: {name} on {deadline}"


@mcp.tool()
def remove_deadline(name: str) -> str:
    """Remove a deadline by name."""
    deadlines = _load_deadlines()
    new_deadlines = [d for d in deadlines if d["name"] != name]
    if len(new_deadlines) == len(deadlines):
        return f"Deadline '{name}' not found"
    _save_deadlines(new_deadlines)
    return f"Removed deadline: {name}"


@mcp.tool()
def git_activity_summary(repo_path: str = ".", days: int = 7) -> str:
    """Summarize git activity in a repository for the past N days.
    Useful for understanding what you've been working on.
    """
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--oneline", "--no-merges", "--author=mav"],
            capture_output=True, text=True, cwd=os.path.expanduser(repo_path)
        )
        commits = result.stdout.strip()

        result2 = subprocess.run(
            ["git", "diff", "--stat", f"HEAD~20", "HEAD"],
            capture_output=True, text=True, cwd=os.path.expanduser(repo_path)
        )
        diff_stat = result2.stdout.strip()

    except Exception as e:
        return f"Error reading git activity: {e}"

    output = f"## Git Activity ({days} days)\n\n"
    output += f"### Commits\n```\n{commits or 'No commits'}\n```\n\n"
    output += f"### File Changes\n```\n{diff_stat or 'No changes'}\n```"
    return output


@mcp.tool()
def progress_check() -> str:
    """Check overall research progress by reading goals and recent activity.
    Returns a status report combining goals, deadlines, and recent work.
    """
    # Read goals
    goals_path = Path(os.path.expanduser("~/Documents/Obsidian Vault/Digital-Self/Goals/goals.md"))
    goals_content = ""
    if goals_path.exists():
        goals_content = goals_path.read_text()

    # Check deadlines
    deadlines = _load_deadlines()
    today = datetime.now().date()
    urgent = []
    for d in deadlines:
        try:
            dl_date = datetime.strptime(d["deadline"], "%Y-%m-%d").date()
            days_left = (dl_date - today).days
            if 0 <= days_left <= 30:
                urgent.append(f"- {d['name']}: {days_left} days left")
        except ValueError:
            continue

    output = "## Progress Check\n\n"
    output += "### Urgent Deadlines (next 30 days)\n"
    output += "\n".join(urgent) if urgent else "None — you're clear!"
    output += "\n\n### Current Goals\n"
    # Extract TODO items from goals
    for line in goals_content.split("\n"):
        if line.strip().startswith("- ["):
            output += line + "\n"

    return output


@mcp.tool()
def draft_email(recipient: str, purpose: str, context: str = "") -> str:
    """Draft an academic email. Provide recipient role (advisor/collaborator/reviewer)
    and purpose. Will reference writing style from Digital Self profile.
    """
    style_path = Path(os.path.expanduser("~/Documents/Obsidian Vault/Digital-Self/Style/writing-style.md"))
    style_info = ""
    if style_path.exists():
        style_info = style_path.read_text()

    return f"""## Email Draft Request

**To:** {recipient}
**Purpose:** {purpose}
**Context:** {context}

**Style Reference:**
{style_info[:500] if style_info else '[No style profile found — please fill in Digital-Self/Style/writing-style.md]'}

---
*Please generate the email draft based on the above. Match the user's communication style.*
"""


if __name__ == "__main__":
    mcp.run()
