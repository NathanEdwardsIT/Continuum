"""Wiki-style [[link]] parsing and resolution."""

from __future__ import annotations

import re

_WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def extract_wiki_links(content: str) -> list[str]:
    """Return unique wiki link targets from note content."""
    seen: set[str] = set()
    links: list[str] = []
    for match in _WIKI_LINK_RE.finditer(content):
        target = match.group(1).strip()
        if target and target.lower() not in seen:
            seen.add(target.lower())
            links.append(target)
    return links


def resolve_wiki_targets(
    targets: list[str],
    title_index: dict[str, int],
) -> list[tuple[int, str]]:
    """Map wiki link text to note IDs using case-insensitive title match."""
    resolved: list[tuple[int, str]] = []
    seen_ids: set[int] = set()
    for target in targets:
        note_id = title_index.get(target.lower())
        if note_id is not None and note_id not in seen_ids:
            seen_ids.add(note_id)
            resolved.append((note_id, target))
    return resolved
