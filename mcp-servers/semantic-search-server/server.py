# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]>=1.0.0", "chromadb>=0.5.0", "sentence-transformers>=3.0.0"]
# ///

import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path

import chromadb
from mcp.server.fastmcp import FastMCP

ZOTERO_DB = os.environ.get("ZOTERO_DB", os.path.expanduser("~/Zotero/zotero.sqlite"))
INDEX_DIR = os.environ.get("SEMANTIC_INDEX", os.path.expanduser("~/.cache/pa-semantic-index"))
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

mcp = FastMCP("semantic-search")

_chroma_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None
_last_index_time: float = 0
INDEX_TTL = 3600  # re-index every hour


def _get_zotero_db() -> sqlite3.Connection:
    tmp = os.path.join(tempfile.gettempdir(), "zotero_semantic_cache.sqlite")
    shutil.copy2(ZOTERO_DB, tmp)
    conn = sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _load_papers() -> list[dict]:
    conn = _get_zotero_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT i.itemID, i.key, i.dateAdded,
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
        HAVING title IS NOT NULL
    """)
    papers = []
    for row in cur.fetchall():
        if row["title"]:
            papers.append({
                "id": row["key"],
                "title": row["title"],
                "abstract": row["abstract"] or "",
                "date": row["date"] or "",
                "added": row["dateAdded"][:10],
            })
    conn.close()
    return papers


def _get_collection() -> chromadb.Collection:
    global _chroma_client, _collection, _last_index_time

    now = time.time()
    needs_reindex = _collection is None or (now - _last_index_time) > INDEX_TTL

    if not needs_reindex:
        return _collection

    Path(INDEX_DIR).mkdir(parents=True, exist_ok=True)
    _chroma_client = chromadb.PersistentClient(path=INDEX_DIR)

    try:
        _collection = _chroma_client.get_collection("papers")
        existing_count = _collection.count()
    except Exception:
        existing_count = 0
        _collection = None

    papers = _load_papers()

    if _collection and existing_count >= len(papers) * 0.9:
        _last_index_time = now
        return _collection

    # Rebuild index
    if _collection:
        _chroma_client.delete_collection("papers")

    _collection = _chroma_client.create_collection(
        name="papers",
        metadata={"hnsw:space": "cosine"},
    )

    batch_size = 100
    for i in range(0, len(papers), batch_size):
        batch = papers[i:i + batch_size]
        docs = [f"{p['title']}. {p['abstract'][:500]}" for p in batch]
        ids = [p["id"] for p in batch]
        metadatas = [{"title": p["title"], "date": p["date"], "added": p["added"]} for p in batch]
        _collection.add(documents=docs, ids=ids, metadatas=metadatas)

    _last_index_time = now
    return _collection


@mcp.tool()
def semantic_search(query: str, n_results: int = 10) -> str:
    """Search papers using natural language semantic similarity.
    Unlike keyword search, this understands meaning — e.g. 'learning abstract concepts from experience'
    will find papers about concept learning even if they don't use those exact words.
    """
    collection = _get_collection()
    results = collection.query(query_texts=[query], n_results=n_results)

    if not results["ids"][0]:
        return "No semantically similar papers found"

    output = []
    for i, (doc_id, distance, metadata) in enumerate(
        zip(results["ids"][0], results["distances"][0], results["metadatas"][0])
    ):
        similarity = 1 - distance
        output.append(
            f"{i+1}. **{metadata['title']}** (similarity: {similarity:.3f})\n"
            f"   Key: {doc_id} | Date: {metadata['date']} | Added: {metadata['added']}"
        )

    return f"## Semantic Search: \"{query}\"\n\nFound {len(output)} relevant papers:\n\n" + "\n\n".join(output)


@mcp.tool()
def find_similar_papers(paper_key: str, n_results: int = 10) -> str:
    """Find papers similar to a given paper in your library.
    Useful for exploring related work or finding papers you might have missed.
    """
    collection = _get_collection()

    try:
        paper = collection.get(ids=[paper_key], include=["documents", "metadatas"])
    except Exception:
        return f"Paper '{paper_key}' not found in the index"

    if not paper["documents"]:
        return f"Paper '{paper_key}' not found in the index"

    doc_text = paper["documents"][0]
    paper_title = paper["metadatas"][0]["title"]

    results = collection.query(query_texts=[doc_text], n_results=n_results + 1)

    output = []
    for doc_id, distance, metadata in zip(
        results["ids"][0], results["distances"][0], results["metadatas"][0]
    ):
        if doc_id == paper_key:
            continue
        similarity = 1 - distance
        output.append(
            f"- **{metadata['title']}** (similarity: {similarity:.3f})\n"
            f"  Key: {doc_id} | Date: {metadata['date']}"
        )

    return f"## Papers similar to: \"{paper_title}\"\n\n" + "\n".join(output[:n_results])


@mcp.tool()
def get_index_stats() -> str:
    """Get statistics about the semantic search index."""
    collection = _get_collection()
    count = collection.count()
    return f"Semantic index contains **{count}** papers.\nModel: {EMBEDDING_MODEL}\nIndex path: {INDEX_DIR}"


if __name__ == "__main__":
    mcp.run()
