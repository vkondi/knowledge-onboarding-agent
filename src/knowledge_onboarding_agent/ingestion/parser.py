"""MarkdownParser: converts a markdown file into a ParsedDocument.

Extracts YAML front matter, document sections, and plain text content.
Does not require NLTK or other heavy NLP dependencies — pure stdlib + PyYAML.
"""

from __future__ import annotations

import html as html_module
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from knowledge_onboarding_agent.models import ParsedDocument, Section

_FRONT_MATTER_RE = re.compile(r"^\s*---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def _extract_front_matter(raw: str) -> tuple[dict[str, Any], str]:
    """Return (front_matter_dict, body_without_front_matter)."""
    match = _FRONT_MATTER_RE.match(raw)
    if match:
        try:
            data = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            data = {}
        return data, raw[match.end():]
    return {}, raw


def _markdown_to_plain_text(md: str) -> str:
    """Strip markdown syntax from *md*, returning clean readable text.

    Preserves the underlying words while removing all markup.
    """
    # Fenced code blocks: remove fences, keep code content
    text = re.sub(r"```[^\n]*\n(.*?)```", r"\1", md, flags=re.DOTALL)
    # Inline code: remove backticks, keep content
    text = re.sub(r"`([^`\n]+)`", r"\1", text)
    # Images: ![alt](url) → alt text
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # Links: [text](url) → text
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    # Heading markers (keep heading text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Bold and italic (keep content)
    text = re.sub(r"\*{1,3}([^*\n]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}([^_\n]+)_{1,3}", r"\1", text)
    # Horizontal rules
    text = re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Blockquote markers
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    # Inline HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # HTML entities
    text = html_module.unescape(text)
    # Collapse 3+ blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_sections(body: str) -> list[Section]:
    """Split markdown *body* into Section objects delimited by headings."""
    matches = list(_HEADING_RE.finditer(body))

    if not matches:
        content = _markdown_to_plain_text(body)
        if content:
            return [Section(heading="", level=0, content=content)]
        return []

    sections: list[Section] = []

    # Preamble: content before the first heading
    preamble_text = body[: matches[0].start()].strip()
    if preamble_text:
        plain = _markdown_to_plain_text(preamble_text)
        if plain:
            sections.append(Section(heading="", level=0, content=plain))

    for i, match in enumerate(matches):
        level = len(match.group(1))
        heading_text = match.group(2).strip()
        content_start = match.end()
        content_end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        body_text = body[content_start:content_end].strip()
        sections.append(
            Section(
                heading=heading_text,
                level=level,
                content=_markdown_to_plain_text(body_text),
            )
        )

    return sections


def _first_h1(body: str) -> str | None:
    match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    return match.group(1).strip() if match else None


class MarkdownParser:
    """Parses a markdown file into a ParsedDocument.

    Extracts:
    - YAML front matter (between ``---`` delimiters at the top of the file)
    - Document title: front matter ``title`` > first H1 > filename stem
    - Sections: content grouped by heading
    - Full plain-text body (all sections concatenated)
    """

    def parse(self, path: Path) -> ParsedDocument:
        """Parse the markdown file at *path*.

        Raises:
            FileNotFoundError: if *path* does not exist.
        """
        raw = path.read_text(encoding="utf-8")
        front_matter, body = _extract_front_matter(raw)
        sections = _extract_sections(body)

        title = (
            str(front_matter.get("title", "")).strip()
            or _first_h1(body)
            or path.stem
        )

        full_text = "\n\n".join(s.content for s in sections if s.content)

        try:
            modified_at = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            modified_at = datetime.now()

        return ParsedDocument(
            source_path=path,
            title=title,
            content=full_text,
            sections=sections,
            front_matter=front_matter,
            modified_at=modified_at,
            word_count=len(full_text.split()),
        )
