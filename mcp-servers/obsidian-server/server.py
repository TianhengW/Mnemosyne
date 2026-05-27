# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]>=1.0.0"]
# ///

import os
import re
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

VAULT_PATH = os.environ.get(
    "OBSIDIAN_VAULT", os.path.expanduser("~/Documents/Obsidian Vault")
)

mcp = FastMCP("obsidian")


def _vault() -> Path:
    return Path(VAULT_PATH)


def _is_note(p: Path) -> bool:
    return p.suffix == ".md" and not p.name.startswith(".")


def _relative(p: Path) -> str:
    return str(p.relative_to(_vault()))


def _extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    fm_text = content[3:end].strip()
    result = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            result[key.strip()] = val.strip()
    return result


def _extract_links(content: str) -> list[str]:
    """Extract [[wikilinks]] from content."""
    return re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", content)


@mcp.tool()
def search_notes(query: str, folder: str = "") -> str:
    """Full-text search across all notes in the vault. Optionally filter by folder."""
    vault = _vault()
    search_path = vault / folder if folder else vault
    if not search_path.exists():
        return f"Folder '{folder}' does not exist"

    results = []
    query_lower = query.lower()

    for p in search_path.rglob("*.md"):
        if not _is_note(p):
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if query_lower in content.lower():
            lines = content.split("\n")
            matching_lines = [
                (i + 1, line.strip())
                for i, line in enumerate(lines)
                if query_lower in line.lower()
            ]
            preview = matching_lines[0][1][:100] if matching_lines else ""
            results.append(
                f"- **{_relative(p)}** (line {matching_lines[0][0]}): {preview}"
            )

    if not results:
        return f"No notes found matching '{query}'"

    return f"Found {len(results)} notes:\n\n" + "\n".join(results[:30])


@mcp.tool()
def get_note(path: str) -> str:
    """Read the full content of a note by its relative path in the vault."""
    note_path = _vault() / path
    if not note_path.exists():
        # Try adding .md extension
        note_path = _vault() / (path + ".md")
    if not note_path.exists():
        return f"Note '{path}' not found"

    content = note_path.read_text(encoding="utf-8")
    return f"# {note_path.stem}\n\n{content}"


@mcp.tool()
def list_notes(folder: str = "", recursive: bool = True) -> str:
    """List all notes in the vault or a specific folder."""
    vault = _vault()
    search_path = vault / folder if folder else vault
    if not search_path.exists():
        return f"Folder '{folder}' does not exist"

    notes = []
    glob_fn = search_path.rglob if recursive else search_path.glob
    for p in sorted(glob_fn("*.md")):
        if not _is_note(p):
            continue
        rel = _relative(p)
        size = p.stat().st_size
        mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d")
        notes.append(f"- {rel} ({size}B, modified: {mtime})")

    if not notes:
        return f"No notes found in '{folder or 'vault'}'"

    return f"Found {len(notes)} notes:\n\n" + "\n".join(notes[:50])


@mcp.tool()
def create_note(path: str, content: str, tags: list[str] | None = None) -> str:
    """Create a new note in the vault. Path is relative to vault root."""
    note_path = _vault() / path
    if not path.endswith(".md"):
        note_path = _vault() / (path + ".md")

    note_path.parent.mkdir(parents=True, exist_ok=True)

    if note_path.exists():
        return f"Note already exists at '{_relative(note_path)}'. Use append_to_note to add content."

    # Build content with optional frontmatter
    final_content = ""
    if tags:
        final_content = f"---\ntags: [{', '.join(tags)}]\ncreated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n---\n\n"
    else:
        final_content = f"---\ncreated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n---\n\n"

    final_content += content
    note_path.write_text(final_content, encoding="utf-8")

    return f"Created note: {_relative(note_path)}"


@mcp.tool()
def append_to_note(path: str, content: str) -> str:
    """Append content to an existing note."""
    note_path = _vault() / path
    if not note_path.exists():
        note_path = _vault() / (path + ".md")
    if not note_path.exists():
        return f"Note '{path}' not found. Use create_note to create it first."

    existing = note_path.read_text(encoding="utf-8")
    note_path.write_text(existing + "\n\n" + content, encoding="utf-8")

    return f"Appended to note: {_relative(note_path)}"


@mcp.tool()
def get_note_links(path: str) -> str:
    """Get all [[wikilinks]] from a note and find which notes link back to it."""
    note_path = _vault() / path
    if not note_path.exists():
        note_path = _vault() / (path + ".md")
    if not note_path.exists():
        return f"Note '{path}' not found"

    content = note_path.read_text(encoding="utf-8")
    outgoing = _extract_links(content)

    # Find backlinks
    note_name = note_path.stem
    backlinks = []
    for p in _vault().rglob("*.md"):
        if p == note_path or not _is_note(p):
            continue
        try:
            other_content = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if f"[[{note_name}]]" in other_content or f"[[{note_name}|" in other_content:
            backlinks.append(_relative(p))

    output = f"## Links in '{path}':\n\n"
    output += f"**Outgoing ({len(outgoing)}):** " + ", ".join(outgoing) if outgoing else "**Outgoing:** None"
    output += "\n\n"
    output += f"**Backlinks ({len(backlinks)}):** " + ", ".join(backlinks) if backlinks else "**Backlinks:** None"

    return output


if __name__ == "__main__":
    mcp.run()
