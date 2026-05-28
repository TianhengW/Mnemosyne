# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]>=1.0.0", "httpx>=0.27.0", "python-dotenv>=1.0.0"]
# ///

import json
import os
import re
from pathlib import Path

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

mcp = FastMCP("notion")

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _headers() -> dict:
    token = os.environ.get("NOTION_TOKEN", "")
    if not token:
        raise ValueError("NOTION_TOKEN 未配置。请在 .env 中设置")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _client() -> httpx.Client:
    return httpx.Client(timeout=30, headers=_headers())


def _rich_text_to_str(rich_text: list[dict]) -> str:
    return "".join(rt.get("plain_text", "") for rt in rich_text)


def _get_page_title(page: dict) -> str:
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            return _rich_text_to_str(prop.get("title", []))
    return "Untitled"


def _blocks_to_markdown(blocks: list[dict]) -> str:
    lines = []
    numbered_counter = 0

    for block in blocks:
        btype = block.get("type", "")
        data = block.get(btype, {})

        if btype == "paragraph":
            text = _rich_text_to_str(data.get("rich_text", []))
            lines.append(text)
            numbered_counter = 0

        elif btype == "heading_1":
            text = _rich_text_to_str(data.get("rich_text", []))
            lines.append(f"# {text}")
            numbered_counter = 0

        elif btype == "heading_2":
            text = _rich_text_to_str(data.get("rich_text", []))
            lines.append(f"## {text}")
            numbered_counter = 0

        elif btype == "heading_3":
            text = _rich_text_to_str(data.get("rich_text", []))
            lines.append(f"### {text}")
            numbered_counter = 0

        elif btype == "bulleted_list_item":
            text = _rich_text_to_str(data.get("rich_text", []))
            lines.append(f"- {text}")
            numbered_counter = 0

        elif btype == "numbered_list_item":
            numbered_counter += 1
            text = _rich_text_to_str(data.get("rich_text", []))
            lines.append(f"{numbered_counter}. {text}")

        elif btype == "to_do":
            text = _rich_text_to_str(data.get("rich_text", []))
            checked = "x" if data.get("checked") else " "
            lines.append(f"- [{checked}] {text}")
            numbered_counter = 0

        elif btype == "code":
            text = _rich_text_to_str(data.get("rich_text", []))
            lang = data.get("language", "")
            lines.append(f"```{lang}\n{text}\n```")
            numbered_counter = 0

        elif btype == "quote":
            text = _rich_text_to_str(data.get("rich_text", []))
            lines.append(f"> {text}")
            numbered_counter = 0

        elif btype == "callout":
            text = _rich_text_to_str(data.get("rich_text", []))
            icon = data.get("icon", {}).get("emoji", "")
            lines.append(f"> {icon} {text}")
            numbered_counter = 0

        elif btype == "divider":
            lines.append("---")
            numbered_counter = 0

        elif btype == "toggle":
            text = _rich_text_to_str(data.get("rich_text", []))
            lines.append(f"<details><summary>{text}</summary></details>")
            numbered_counter = 0

        elif btype == "image":
            url = ""
            if data.get("type") == "external":
                url = data.get("external", {}).get("url", "")
            elif data.get("type") == "file":
                url = data.get("file", {}).get("url", "")
            caption = _rich_text_to_str(data.get("caption", []))
            lines.append(f"![{caption}]({url})")
            numbered_counter = 0

        else:
            if btype not in ("child_page", "child_database", "table_of_contents", "breadcrumb", "column_list", "column"):
                text = _rich_text_to_str(data.get("rich_text", []))
                if text:
                    lines.append(text)
            numbered_counter = 0

    return "\n\n".join(lines)


def _markdown_to_blocks(markdown: str) -> list[dict]:
    blocks = []
    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            lang = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": "\n".join(code_lines)}}],
                    "language": lang or "plain text",
                },
            })
            i += 1
            continue

        if line.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]},
            })
        elif line.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]},
            })
        elif line.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]},
            })
        elif line.startswith("- ["):
            match = re.match(r"- \[(x| )\] (.+)", line)
            if match:
                blocks.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"type": "text", "text": {"content": match.group(2)}}],
                        "checked": match.group(1) == "x",
                    },
                })
            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]},
                })
        elif line.startswith("- "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]},
            })
        elif re.match(r"^\d+\. ", line):
            text = re.sub(r"^\d+\. ", "", line)
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
            })
        elif line.startswith("> "):
            blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]},
            })
        elif line.startswith("---"):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        elif line.strip():
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]},
            })

        i += 1

    return blocks


def _format_page_summary(page: dict) -> str:
    title = _get_page_title(page)
    page_id = page.get("id", "")
    url = page.get("url", "")
    last_edited = page.get("last_edited_time", "")[:10]
    return f"- **{title}** (id: `{page_id}`, edited: {last_edited}) [link]({url})"


@mcp.tool()
def notion_search(query: str, filter_type: str = "") -> str:
    """Search Notion pages and databases by keyword.

    Args:
        query: Search keyword
        filter_type: Optional filter - "page" or "database". Empty for all.
    """
    payload: dict = {"query": query, "page_size": 20}
    if filter_type in ("page", "database"):
        payload["filter"] = {"value": filter_type, "property": "object"}

    with _client() as client:
        resp = client.post(f"{NOTION_API_BASE}/search", json=payload)
        if resp.status_code != 200:
            return f"Error: {resp.status_code} — {resp.text}"
        data = resp.json()

    results = data.get("results", [])
    if not results:
        return f"No results found for '{query}'"

    output = f"Found {len(results)} results for '{query}':\n\n"
    for item in results:
        obj_type = item.get("object", "")
        if obj_type == "page":
            output += _format_page_summary(item) + "\n"
        elif obj_type == "database":
            title_parts = item.get("title", [])
            title = _rich_text_to_str(title_parts)
            output += f"- 📊 **[DB] {title}** (id: `{item['id']}`)\n"

    return output


@mcp.tool()
def notion_get_page(page_id: str) -> str:
    """Get full content of a Notion page (properties + body blocks).

    Args:
        page_id: The Notion page ID (32-char hex, with or without dashes)
    """
    with _client() as client:
        page_resp = client.get(f"{NOTION_API_BASE}/pages/{page_id}")
        if page_resp.status_code != 200:
            return f"Error fetching page: {page_resp.status_code} — {page_resp.text}"

        page = page_resp.json()
        title = _get_page_title(page)

        all_blocks = []
        has_more = True
        start_cursor = None
        while has_more:
            params = {"page_size": 100}
            if start_cursor:
                params["start_cursor"] = start_cursor
            blocks_resp = client.get(f"{NOTION_API_BASE}/blocks/{page_id}/children", params=params)
            if blocks_resp.status_code != 200:
                break
            blocks_data = blocks_resp.json()
            all_blocks.extend(blocks_data.get("results", []))
            has_more = blocks_data.get("has_more", False)
            start_cursor = blocks_data.get("next_cursor")

    content = _blocks_to_markdown(all_blocks)
    url = page.get("url", "")
    last_edited = page.get("last_edited_time", "")[:10]

    output = f"# {title}\n\n"
    output += f"*ID: `{page_id}` | Last edited: {last_edited} | [Open in Notion]({url})*\n\n---\n\n"
    output += content

    return output


@mcp.tool()
def notion_get_database(database_id: str, page_size: int = 20) -> str:
    """Get database schema and recent entries.

    Args:
        database_id: The Notion database ID
        page_size: Number of entries to return (default 20, max 100)
    """
    with _client() as client:
        db_resp = client.get(f"{NOTION_API_BASE}/databases/{database_id}")
        if db_resp.status_code != 200:
            return f"Error: {db_resp.status_code} — {db_resp.text}"
        db = db_resp.json()

        query_resp = client.post(
            f"{NOTION_API_BASE}/databases/{database_id}/query",
            json={"page_size": min(page_size, 100)},
        )
        if query_resp.status_code != 200:
            return f"Error querying: {query_resp.status_code} — {query_resp.text}"
        query_data = query_resp.json()

    title = _rich_text_to_str(db.get("title", []))
    props = db.get("properties", {})

    output = f"# 📊 Database: {title}\n\n"
    output += f"**ID:** `{database_id}`\n\n"
    output += "**Properties:**\n"
    for name, prop in props.items():
        output += f"- {name} ({prop['type']})\n"

    output += f"\n**Entries ({len(query_data.get('results', []))}):**\n\n"
    for page in query_data.get("results", []):
        output += _format_page_summary(page) + "\n"

    return output


@mcp.tool()
def notion_create_page(
    parent_id: str,
    title: str,
    content: str = "",
    parent_type: str = "page",
    properties: str = "",
) -> str:
    """Create a new page in Notion.

    Args:
        parent_id: Parent page ID or database ID
        title: Page title
        content: Page body in Markdown format (optional)
        parent_type: "page" or "database" (default "page")
        properties: JSON string of additional database properties (optional, for database parents)
    """
    if parent_type == "database":
        parent = {"database_id": parent_id}
        page_properties = {"title": {"title": [{"type": "text", "text": {"content": title}}]}}
        if properties:
            try:
                extra_props = json.loads(properties)
                page_properties.update(extra_props)
            except json.JSONDecodeError:
                pass
    else:
        parent = {"page_id": parent_id}
        page_properties = {"title": {"title": [{"type": "text", "text": {"content": title}}]}}

    payload: dict = {"parent": parent, "properties": page_properties}

    if content:
        blocks = _markdown_to_blocks(content)
        if blocks:
            payload["children"] = blocks[:100]

    with _client() as client:
        resp = client.post(f"{NOTION_API_BASE}/pages", json=payload)
        if resp.status_code != 200:
            return f"Error creating page: {resp.status_code} — {resp.text}"
        page = resp.json()

    return f"Created page: **{title}** (id: `{page['id']}`)\n[Open in Notion]({page.get('url', '')})"


@mcp.tool()
def notion_update_page(page_id: str, content: str) -> str:
    """Append content to an existing Notion page.

    Args:
        page_id: The page ID to append to
        content: Content in Markdown format to append
    """
    blocks = _markdown_to_blocks(content)
    if not blocks:
        return "No content to append"

    with _client() as client:
        resp = client.patch(
            f"{NOTION_API_BASE}/blocks/{page_id}/children",
            json={"children": blocks[:100]},
        )
        if resp.status_code != 200:
            return f"Error appending: {resp.status_code} — {resp.text}"

    return f"Appended {len(blocks)} blocks to page `{page_id}`"


@mcp.tool()
def notion_list_databases() -> str:
    """List all databases accessible to the integration."""
    with _client() as client:
        resp = client.post(
            f"{NOTION_API_BASE}/search",
            json={"filter": {"value": "database", "property": "object"}, "page_size": 50},
        )
        if resp.status_code != 200:
            return f"Error: {resp.status_code} — {resp.text}"
        data = resp.json()

    results = data.get("results", [])
    if not results:
        return "No databases found. Make sure you've connected the integration to your Notion pages."

    output = f"Found {len(results)} databases:\n\n"
    for db in results:
        title = _rich_text_to_str(db.get("title", []))
        db_id = db.get("id", "")
        url = db.get("url", "")
        output += f"- 📊 **{title}** (id: `{db_id}`) [link]({url})\n"

    return output


@mcp.tool()
def notion_query_database(database_id: str, filter_json: str = "", sort_json: str = "") -> str:
    """Query a Notion database with optional filter and sort.

    Args:
        database_id: The database ID to query
        filter_json: Optional Notion filter object as JSON string (see Notion API docs)
        sort_json: Optional sort array as JSON string
    """
    payload: dict = {"page_size": 50}

    if filter_json:
        try:
            payload["filter"] = json.loads(filter_json)
        except json.JSONDecodeError:
            return "Invalid filter_json format"

    if sort_json:
        try:
            payload["sorts"] = json.loads(sort_json)
        except json.JSONDecodeError:
            return "Invalid sort_json format"

    with _client() as client:
        resp = client.post(f"{NOTION_API_BASE}/databases/{database_id}/query", json=payload)
        if resp.status_code != 200:
            return f"Error: {resp.status_code} — {resp.text}"
        data = resp.json()

    results = data.get("results", [])
    if not results:
        return "No entries match the query"

    output = f"Found {len(results)} entries:\n\n"
    for page in results:
        output += _format_page_summary(page) + "\n"

    return output


@mcp.tool()
def notion_list_pages(database_id: str = "", page_size: int = 30) -> str:
    """List pages — either from a specific database or all accessible pages.

    Args:
        database_id: Optional database ID. If empty, lists all recent pages.
        page_size: Number of pages to return (default 30)
    """
    with _client() as client:
        if database_id:
            resp = client.post(
                f"{NOTION_API_BASE}/databases/{database_id}/query",
                json={"page_size": min(page_size, 100)},
            )
        else:
            resp = client.post(
                f"{NOTION_API_BASE}/search",
                json={
                    "filter": {"value": "page", "property": "object"},
                    "sort": {"direction": "descending", "timestamp": "last_edited_time"},
                    "page_size": min(page_size, 100),
                },
            )

        if resp.status_code != 200:
            return f"Error: {resp.status_code} — {resp.text}"
        data = resp.json()

    results = data.get("results", [])
    if not results:
        return "No pages found"

    source = f"database `{database_id}`" if database_id else "all accessible pages"
    output = f"Found {len(results)} pages from {source}:\n\n"
    for page in results:
        output += _format_page_summary(page) + "\n"

    return output


if __name__ == "__main__":
    mcp.run()
