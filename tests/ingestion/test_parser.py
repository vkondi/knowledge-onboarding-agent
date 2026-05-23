"""Tests for knowledge_onboarding_agent.ingestion.parser."""

from pathlib import Path

import pytest

from knowledge_onboarding_agent.ingestion.parser import (
    MarkdownParser,
    _extract_front_matter,
    _markdown_to_plain_text,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# _markdown_to_plain_text
# ---------------------------------------------------------------------------

class TestMarkdownToPlainText:
    def test_strips_heading_markers(self):
        assert _markdown_to_plain_text("## My Heading") == "My Heading"

    def test_strips_bold_keeps_content(self):
        text = _markdown_to_plain_text("This is **bold** text.")
        assert "**" not in text
        assert "bold" in text

    def test_strips_italic_keeps_content(self):
        text = _markdown_to_plain_text("This is *italic* text.")
        assert "*" not in text
        assert "italic" in text

    def test_converts_link_to_text(self):
        text = _markdown_to_plain_text("[Click here](https://example.com)")
        assert "Click here" in text
        assert "https://" not in text

    def test_strips_image_keeps_alt_text(self):
        text = _markdown_to_plain_text("![diagram](image.png)")
        assert "![" not in text
        assert "diagram" in text

    def test_preserves_inline_code_content(self):
        text = _markdown_to_plain_text("Call `print()` to output text.")
        assert "print()" in text
        assert "`" not in text

    def test_strips_blockquote_marker(self):
        text = _markdown_to_plain_text("> Important note here.")
        assert ">" not in text
        assert "Important note here." in text

    def test_strips_horizontal_rule(self):
        text = _markdown_to_plain_text("Above\n\n---\n\nBelow")
        assert "---" not in text
        assert "Above" in text
        assert "Below" in text


# ---------------------------------------------------------------------------
# _extract_front_matter
# ---------------------------------------------------------------------------

class TestExtractFrontMatter:
    def test_extracts_front_matter_fields(self):
        raw = "---\ntitle: My Doc\ntags: [a, b]\n---\n# Body"
        fm, body = _extract_front_matter(raw)
        assert fm["title"] == "My Doc"
        assert fm["tags"] == ["a", "b"]
        assert "title:" not in body

    def test_body_preserved_after_extraction(self):
        raw = "---\ntitle: Test\n---\n# Heading\nContent here."
        _, body = _extract_front_matter(raw)
        assert "# Heading" in body
        assert "Content here." in body

    def test_returns_empty_dict_when_no_front_matter(self):
        raw = "# Just a heading\nNo front matter here."
        fm, body = _extract_front_matter(raw)
        assert fm == {}
        assert "# Just a heading" in body

    def test_handles_malformed_front_matter_gracefully(self):
        raw = "---\n: {invalid yaml\n---\n# Body"
        fm, body = _extract_front_matter(raw)
        assert isinstance(fm, dict)  # never raises


# ---------------------------------------------------------------------------
# MarkdownParser
# ---------------------------------------------------------------------------

class TestMarkdownParser:
    @pytest.fixture
    def parser(self) -> MarkdownParser:
        return MarkdownParser()

    def test_title_from_front_matter_takes_precedence(self, parser, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("---\ntitle: FM Title\n---\n# H1 Title\nContent.", encoding="utf-8")
        doc = parser.parse(f)
        assert doc.title == "FM Title"

    def test_title_from_first_h1(self, parser, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("# H1 Title\nContent here.", encoding="utf-8")
        doc = parser.parse(f)
        assert doc.title == "H1 Title"

    def test_title_fallback_to_filename_stem(self, parser, tmp_path):
        f = tmp_path / "my-document.md"
        f.write_text("No headings, no front matter.", encoding="utf-8")
        doc = parser.parse(f)
        assert doc.title == "my-document"

    def test_sections_extracted_with_correct_headings(self, parser, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text(
            "# Introduction\nIntro text.\n\n## Details\nDetails text.",
            encoding="utf-8",
        )
        doc = parser.parse(f)
        headings = [s.heading for s in doc.sections]
        assert "Introduction" in headings
        assert "Details" in headings

    def test_section_levels_correct(self, parser, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("# H1\nA.\n## H2\nB.\n### H3\nC.", encoding="utf-8")
        doc = parser.parse(f)
        levels = {s.heading: s.level for s in doc.sections}
        assert levels["H1"] == 1
        assert levels["H2"] == 2
        assert levels["H3"] == 3

    def test_no_headings_produces_single_section(self, parser, tmp_path):
        f = tmp_path / "plain.md"
        f.write_text("Just plain text.\n\nAnother paragraph.", encoding="utf-8")
        doc = parser.parse(f)
        assert len(doc.sections) == 1
        assert doc.sections[0].level == 0

    def test_front_matter_preserved_on_document(self, parser, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text(
            "---\ntags: [python, ai]\ndate: 2026-01-01\n---\nContent.",
            encoding="utf-8",
        )
        doc = parser.parse(f)
        assert doc.front_matter["tags"] == ["python", "ai"]

    def test_word_count_is_positive(self, parser, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("# Title\nOne two three four five.", encoding="utf-8")
        doc = parser.parse(f)
        assert doc.word_count > 0

    def test_source_path_preserved(self, parser, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("# Title\nContent.", encoding="utf-8")
        doc = parser.parse(f)
        assert doc.source_path == f

    def test_markdown_stripped_from_section_content(self, parser, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("# Title\nThis is **bold** and [a link](http://x.com).", encoding="utf-8")
        doc = parser.parse(f)
        assert "**" not in doc.content
        assert "http://" not in doc.content
        assert "bold" in doc.content
        assert "a link" in doc.content

    def test_parse_simple_fixture(self, parser):
        doc = parser.parse(FIXTURES / "simple.md")
        assert "Getting Started" in doc.title
        assert doc.word_count > 0
        assert len(doc.sections) >= 3  # intro + at least 2 ## sections
        assert doc.front_matter.get("tags") is not None

    def test_parse_no_headings_fixture(self, parser):
        doc = parser.parse(FIXTURES / "no_headings.md")
        assert doc.word_count > 0
        assert len(doc.sections) == 1
        assert doc.sections[0].level == 0

    def test_parse_long_article_fixture(self, parser):
        doc = parser.parse(FIXTURES / "long_article.md")
        assert doc.word_count > 400
        assert len(doc.sections) > 3
