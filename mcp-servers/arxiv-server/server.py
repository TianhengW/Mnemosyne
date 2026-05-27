# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]>=1.0.0", "httpx>=0.27.0"]
# ///

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("arxiv")

TOPICS = [
    "world model",
    "concept reasoning",
    "VLM reasoning",
    "reinforcement learning reasoning",
    "test-time training",
    "self-evolving agent",
    "latent reasoning",
    "vision language action",
]

ARXIV_CATEGORIES = ["cs.AI", "cs.LG", "cs.CV", "cs.CL", "cs.RO"]

CACHE_DIR = Path(os.environ.get("ARXIV_CACHE", os.path.expanduser("~/.cache/arxiv-mcp")))
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _parse_arxiv_atom(xml_text: str) -> list[dict]:
    """Parse arXiv Atom feed into paper dicts."""
    papers = []
    entries = re.findall(r"<entry>(.*?)</entry>", xml_text, re.DOTALL)
    for entry in entries:
        title = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
        summary = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
        authors = re.findall(r"<name>(.*?)</name>", entry)
        arxiv_id = re.search(r"<id>(.*?)</id>", entry)
        published = re.search(r"<published>(.*?)</published>", entry)
        categories = re.findall(r'<category[^>]*term="([^"]*)"', entry)

        if title:
            papers.append({
                "title": re.sub(r"\s+", " ", title.group(1)).strip(),
                "abstract": re.sub(r"\s+", " ", summary.group(1)).strip() if summary else "",
                "authors": authors[:5],
                "arxiv_id": arxiv_id.group(1).split("/abs/")[-1] if arxiv_id else "",
                "published": published.group(1)[:10] if published else "",
                "categories": categories,
                "url": f"https://arxiv.org/abs/{arxiv_id.group(1).split('/abs/')[-1]}" if arxiv_id else "",
            })
    return papers


@mcp.tool()
def search_arxiv(query: str, max_results: int = 15) -> str:
    """Search arXiv for papers matching a query. Good for finding latest work on a topic."""
    url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    with httpx.Client(timeout=30) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()

    papers = _parse_arxiv_atom(resp.text)

    if not papers:
        return f"No papers found on arXiv for '{query}'"

    output = []
    for p in papers:
        authors_str = ", ".join(p["authors"][:3])
        if len(p["authors"]) > 3:
            authors_str += " et al."
        abstract_preview = p["abstract"][:150] + "..." if len(p["abstract"]) > 150 else p["abstract"]
        output.append(
            f"**{p['title']}**\n"
            f"  {authors_str} | {p['published']} | {p['arxiv_id']}\n"
            f"  Categories: {', '.join(p['categories'][:3])}\n"
            f"  {abstract_preview}"
        )

    return f"Found {len(papers)} papers on arXiv:\n\n" + "\n\n".join(output)


@mcp.tool()
def get_arxiv_paper(arxiv_id: str) -> str:
    """Get full details of an arXiv paper by its ID (e.g. '2401.12345')."""
    url = "https://export.arxiv.org/api/query"
    params = {"id_list": arxiv_id}

    with httpx.Client(timeout=30) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()

    papers = _parse_arxiv_atom(resp.text)
    if not papers:
        return f"Paper {arxiv_id} not found"

    p = papers[0]
    authors_str = ", ".join(p["authors"])

    return f"""# {p['title']}

**Authors:** {authors_str}
**Published:** {p['published']}
**arXiv ID:** {p['arxiv_id']}
**URL:** {p['url']}
**Categories:** {', '.join(p['categories'])}

## Abstract
{p['abstract']}
"""


@mcp.tool()
def get_daily_papers(topic: str = "", date: str = "") -> str:
    """Get recent papers from arXiv in the user's research areas.
    If topic is empty, searches across all configured topics.
    Date format: YYYY-MM-DD (defaults to yesterday).
    """
    if not topic:
        topics_to_search = TOPICS[:4]
    else:
        topics_to_search = [topic]

    all_papers = []
    with httpx.Client(timeout=30) as client:
        for t in topics_to_search:
            cat_filter = " OR ".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
            query = f"all:\"{t}\" AND ({cat_filter})"
            params = {
                "search_query": query,
                "start": 0,
                "max_results": 5,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            try:
                resp = client.get("https://export.arxiv.org/api/query", params=params)
                resp.raise_for_status()
                papers = _parse_arxiv_atom(resp.text)
                for p in papers:
                    p["matched_topic"] = t
                all_papers.extend(papers)
            except Exception:
                continue

    # Deduplicate by arxiv_id
    seen = set()
    unique = []
    for p in all_papers:
        if p["arxiv_id"] not in seen:
            seen.add(p["arxiv_id"])
            unique.append(p)

    if not unique:
        return "No recent papers found for your research topics"

    output = []
    for p in unique[:20]:
        authors_str = ", ".join(p["authors"][:2])
        if len(p["authors"]) > 2:
            authors_str += " et al."
        output.append(
            f"- **{p['title']}** ({authors_str}, {p['published']})\n"
            f"  Topic: {p.get('matched_topic', 'N/A')} | {p['arxiv_id']}"
        )

    return f"## Recent Papers ({len(unique)} found)\n\n" + "\n\n".join(output)


@mcp.tool()
def get_huggingface_daily_papers(date: str = "") -> str:
    """Fetch trending papers from HuggingFace Daily Papers.
    Date format: YYYY-MM-DD (defaults to today).
    """
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    url = f"https://huggingface.co/api/daily_papers?date={date}"

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        return f"Failed to fetch HuggingFace daily papers: {e}"

    if not data:
        return f"No papers found for date {date}"

    output = []
    for item in data[:25]:
        paper = item.get("paper", {})
        title = paper.get("title", "Unknown")
        authors = paper.get("authors", [])
        author_names = [a.get("name", "") for a in authors[:3]]
        authors_str = ", ".join(author_names)
        if len(authors) > 3:
            authors_str += " et al."
        abstract = paper.get("summary", "")[:150]
        arxiv_id = paper.get("id", "")
        upvotes = item.get("paper", {}).get("upvotes", 0)

        output.append(
            f"- **{title}** ({authors_str})\n"
            f"  arXiv: {arxiv_id} | Upvotes: {upvotes}\n"
            f"  {abstract}..."
        )

    return f"## HuggingFace Daily Papers ({date}) — {len(data)} papers\n\n" + "\n\n".join(output)


@mcp.tool()
def track_research_topics() -> str:
    """Show the configured research topics being tracked."""
    output = "## Tracked Research Topics\n\n"
    output += "These topics are monitored for new papers:\n\n"
    for t in TOPICS:
        output += f"- {t}\n"
    output += f"\n**arXiv Categories:** {', '.join(ARXIV_CATEGORIES)}"
    return output


if __name__ == "__main__":
    mcp.run()
