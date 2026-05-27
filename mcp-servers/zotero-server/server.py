# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]>=1.0.0"]
# ///

import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP

ZOTERO_DB = os.environ.get("ZOTERO_DB", os.path.expanduser("~/Zotero/zotero.sqlite"))
CACHE_TTL = 60  # refresh cached DB copy every 60 seconds

mcp = FastMCP("zotero")

_cache_path: str | None = None
_cache_time: float = 0


def _get_db() -> sqlite3.Connection:
    """Get a connection to a read-only copy of the Zotero database."""
    global _cache_path, _cache_time

    now = time.time()
    if _cache_path is None or (now - _cache_time) > CACHE_TTL:
        tmp = os.path.join(tempfile.gettempdir(), "zotero_mcp_cache.sqlite")
        shutil.copy2(ZOTERO_DB, tmp)
        _cache_path = tmp
        _cache_time = now

    conn = sqlite3.connect(f"file:{_cache_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


@mcp.tool()
def search_papers(query: str, limit: int = 20) -> str:
    """Search papers by title, abstract, or author name. Returns matching papers with basic info."""
    conn = _get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT i.itemID, i.key, i.dateAdded,
            MAX(CASE WHEN f.fieldName = 'title' THEN idv.value END) as title,
            MAX(CASE WHEN f.fieldName = 'abstractNote' THEN idv.value END) as abstract,
            MAX(CASE WHEN f.fieldName = 'date' THEN idv.value END) as date
        FROM items i
        JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        JOIN itemData id ON i.itemID = id.itemID
        JOIN itemDataValues idv ON id.valueID = idv.valueID
        JOIN fields f ON id.fieldID = f.fieldID
        WHERE it.typeName IN ('journalArticle', 'conferencePaper', 'preprint', 'book', 'bookSection')
        GROUP BY i.itemID
        HAVING title LIKE ? OR abstract LIKE ?
        ORDER BY i.dateAdded DESC
        LIMIT ?
    """, (f"%{query}%", f"%{query}%", limit))

    results = cur.fetchall()

    if not results:
        cur.execute("""
            SELECT DISTINCT i.itemID, i.key, i.dateAdded,
                MAX(CASE WHEN f.fieldName = 'title' THEN idv.value END) as title,
                MAX(CASE WHEN f.fieldName = 'abstractNote' THEN idv.value END) as abstract,
                MAX(CASE WHEN f.fieldName = 'date' THEN idv.value END) as date
            FROM items i
            JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            JOIN itemData id ON i.itemID = id.itemID
            JOIN itemDataValues idv ON id.valueID = idv.valueID
            JOIN fields f ON id.fieldID = f.fieldID
            JOIN itemCreators ic ON i.itemID = ic.itemID
            JOIN creators c ON ic.creatorID = c.creatorID
            WHERE it.typeName IN ('journalArticle', 'conferencePaper', 'preprint', 'book', 'bookSection')
              AND (c.firstName || ' ' || c.lastName LIKE ? OR c.lastName LIKE ?)
            GROUP BY i.itemID
            ORDER BY i.dateAdded DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        results = cur.fetchall()

    conn.close()

    if not results:
        return f"No papers found matching '{query}'"

    output = []
    for r in results:
        abstract_preview = (r["abstract"] or "")[:150]
        if len(r["abstract"] or "") > 150:
            abstract_preview += "..."
        output.append(
            f"**{r['title']}**\n"
            f"  Key: {r['key']} | Date: {r['date'] or 'N/A'} | Added: {r['dateAdded'][:10]}\n"
            f"  Abstract: {abstract_preview}"
        )

    return f"Found {len(results)} papers:\n\n" + "\n\n".join(output)


@mcp.tool()
def get_paper_details(paper_key: str) -> str:
    """Get detailed metadata for a paper by its Zotero key."""
    conn = _get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT i.itemID, i.key, i.dateAdded, it.typeName,
            MAX(CASE WHEN f.fieldName = 'title' THEN idv.value END) as title,
            MAX(CASE WHEN f.fieldName = 'abstractNote' THEN idv.value END) as abstract,
            MAX(CASE WHEN f.fieldName = 'date' THEN idv.value END) as date,
            MAX(CASE WHEN f.fieldName = 'DOI' THEN idv.value END) as doi,
            MAX(CASE WHEN f.fieldName = 'url' THEN idv.value END) as url,
            MAX(CASE WHEN f.fieldName = 'publicationTitle' THEN idv.value END) as publication,
            MAX(CASE WHEN f.fieldName = 'volume' THEN idv.value END) as volume,
            MAX(CASE WHEN f.fieldName = 'pages' THEN idv.value END) as pages
        FROM items i
        JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        JOIN itemData id ON i.itemID = id.itemID
        JOIN itemDataValues idv ON id.valueID = idv.valueID
        JOIN fields f ON id.fieldID = f.fieldID
        WHERE i.key = ?
        GROUP BY i.itemID
    """, (paper_key,))

    row = cur.fetchone()
    if not row:
        conn.close()
        return f"Paper with key '{paper_key}' not found"

    # Get authors
    cur.execute("""
        SELECT c.firstName, c.lastName, ct.creatorType
        FROM itemCreators ic
        JOIN creators c ON ic.creatorID = c.creatorID
        JOIN creatorTypes ct ON ic.creatorTypeID = ct.creatorTypeID
        WHERE ic.itemID = ?
        ORDER BY ic.orderIndex
    """, (row["itemID"],))
    authors = [f"{a['firstName']} {a['lastName']}" for a in cur.fetchall()]

    # Get tags
    cur.execute("""
        SELECT t.name FROM tags t
        JOIN itemTags it ON t.tagID = it.tagID
        WHERE it.itemID = ?
    """, (row["itemID"],))
    tags = [t["name"] for t in cur.fetchall()]

    # Get collections
    cur.execute("""
        SELECT c.collectionName FROM collections c
        JOIN collectionItems ci ON c.collectionID = ci.collectionID
        WHERE ci.itemID = ?
    """, (row["itemID"],))
    collections = [c["collectionName"] for c in cur.fetchall()]

    conn.close()

    output = f"""# {row['title']}

**Type:** {row['typeName']}
**Authors:** {', '.join(authors) if authors else 'N/A'}
**Date:** {row['date'] or 'N/A'}
**Publication:** {row['publication'] or 'N/A'}
**DOI:** {row['doi'] or 'N/A'}
**URL:** {row['url'] or 'N/A'}
**Added:** {row['dateAdded']}
**Collections:** {', '.join(collections) if collections else 'None'}
**Tags:** {', '.join(tags) if tags else 'None'}

## Abstract
{row['abstract'] or 'No abstract available'}
"""
    return output


@mcp.tool()
def get_annotations(paper_key: str) -> str:
    """Get all highlights and annotations for a paper by its Zotero key."""
    conn = _get_db()
    cur = conn.cursor()

    # Find the item and its attachments
    cur.execute("""
        SELECT ia.text, ia.comment, ia.pageLabel, ia.color, ia.type
        FROM itemAnnotations ia
        JOIN items attachment ON ia.parentItemID = attachment.itemID
        JOIN itemAttachments iatt ON attachment.itemID = iatt.itemID
        JOIN items parent ON iatt.parentItemID = parent.itemID
        WHERE parent.key = ?
        ORDER BY ia.sortIndex
    """, (paper_key,))

    annotations = cur.fetchall()
    conn.close()

    if not annotations:
        return f"No annotations found for paper '{paper_key}'"

    output = []
    for ann in annotations:
        page_info = f" (p.{ann['pageLabel']})" if ann["pageLabel"] else ""
        text = ann["text"] or ""
        comment = ann["comment"] or ""

        if text and comment:
            output.append(f"- **Highlight{page_info}:** {text}\n  **Note:** {comment}")
        elif text:
            output.append(f"- **Highlight{page_info}:** {text}")
        elif comment:
            output.append(f"- **Note{page_info}:** {comment}")

    return f"Found {len(annotations)} annotations:\n\n" + "\n\n".join(output)


@mcp.tool()
def list_collections() -> str:
    """List all Zotero collections with paper counts."""
    conn = _get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT c.collectionID, c.collectionName, COUNT(ci.itemID) as paperCount
        FROM collections c
        LEFT JOIN collectionItems ci ON c.collectionID = ci.collectionID
        GROUP BY c.collectionID
        ORDER BY c.collectionName
    """)

    collections = cur.fetchall()
    conn.close()

    output = []
    for c in collections:
        output.append(f"- **{c['collectionName']}** ({c['paperCount']} items) [ID: {c['collectionID']}]")

    return f"Total {len(collections)} collections:\n\n" + "\n".join(output)


@mcp.tool()
def get_collection_papers(collection_name: str, limit: int = 30) -> str:
    """Get all papers in a specific collection by name."""
    conn = _get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT i.itemID, i.key, i.dateAdded,
            MAX(CASE WHEN f.fieldName = 'title' THEN idv.value END) as title,
            MAX(CASE WHEN f.fieldName = 'date' THEN idv.value END) as date
        FROM items i
        JOIN collectionItems ci ON i.itemID = ci.itemID
        JOIN collections c ON ci.collectionID = c.collectionID
        JOIN itemData id ON i.itemID = id.itemID
        JOIN itemDataValues idv ON id.valueID = idv.valueID
        JOIN fields f ON id.fieldID = f.fieldID
        JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        WHERE c.collectionName LIKE ?
          AND it.typeName IN ('journalArticle', 'conferencePaper', 'preprint', 'book', 'bookSection')
        GROUP BY i.itemID
        ORDER BY i.dateAdded DESC
        LIMIT ?
    """, (f"%{collection_name}%", limit))

    results = cur.fetchall()
    conn.close()

    if not results:
        return f"No papers found in collection matching '{collection_name}'"

    output = []
    for r in results:
        output.append(f"- [{r['key']}] **{r['title']}** ({r['date'] or 'N/A'})")

    return f"Collection '{collection_name}' — {len(results)} papers:\n\n" + "\n".join(output)


@mcp.tool()
def get_recent_papers(days: int = 7, limit: int = 20) -> str:
    """Get papers added in the last N days."""
    conn = _get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT i.itemID, i.key, i.dateAdded,
            MAX(CASE WHEN f.fieldName = 'title' THEN idv.value END) as title,
            MAX(CASE WHEN f.fieldName = 'date' THEN idv.value END) as date
        FROM items i
        JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
        JOIN itemData id ON i.itemID = id.itemID
        JOIN itemDataValues idv ON id.valueID = idv.valueID
        JOIN fields f ON id.fieldID = f.fieldID
        WHERE it.typeName IN ('journalArticle', 'conferencePaper', 'preprint', 'book', 'bookSection')
          AND i.dateAdded >= datetime('now', ?)
        GROUP BY i.itemID
        ORDER BY i.dateAdded DESC
        LIMIT ?
    """, (f"-{days} days", limit))

    results = cur.fetchall()
    conn.close()

    if not results:
        return f"No papers added in the last {days} days"

    output = []
    for r in results:
        output.append(f"- [{r['key']}] **{r['title']}** (added: {r['dateAdded'][:10]})")

    return f"Papers added in last {days} days ({len(results)} found):\n\n" + "\n".join(output)


@mcp.tool()
def get_paper_tags(paper_key: str) -> str:
    """Get all tags for a specific paper."""
    conn = _get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT t.name, t.type
        FROM tags t
        JOIN itemTags it ON t.tagID = it.tagID
        JOIN items i ON it.itemID = i.itemID
        WHERE i.key = ?
        ORDER BY t.name
    """, (paper_key,))

    tags = cur.fetchall()
    conn.close()

    if not tags:
        return f"No tags found for paper '{paper_key}'"

    return "Tags: " + ", ".join(t["name"] for t in tags)


if __name__ == "__main__":
    mcp.run()
