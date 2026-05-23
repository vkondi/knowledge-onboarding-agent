"""Tests for knowledge_onboarding_agent.ingestion.chunker."""

from datetime import datetime
from pathlib import Path

import pytest

from knowledge_onboarding_agent.ingestion.chunker import SentenceWindowChunker, _split_into_units, _word_count
from knowledge_onboarding_agent.ingestion.parser import MarkdownParser
from knowledge_onboarding_agent.models import ParsedDocument, Section

FIXTURES = Path(__file__).parent.parent / "fixtures"


def make_document(
    content: str,
    sections: list[Section] | None = None,
    path: Path | None = None,
) -> ParsedDocument:
    p = path or Path("test_doc.md")
    if sections is None:
        sections = [Section(heading="", level=0, content=content)]
    return ParsedDocument(
        source_path=p,
        title="Test Document",
        content=content,
        sections=sections,
        front_matter={},
        modified_at=datetime.now(),
        word_count=len(content.split()),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestWordCount:
    def test_counts_words(self):
        assert _word_count("one two three") == 3

    def test_empty_string(self):
        assert _word_count("") == 0

    def test_extra_whitespace(self):
        assert _word_count("  one  two  ") == 2


class TestSplitIntoUnits:
    def test_splits_on_paragraph_breaks(self):
        text = "First paragraph.\n\nSecond paragraph."
        units = _split_into_units(text)
        assert len(units) == 2

    def test_empty_text_returns_empty_list(self):
        assert _split_into_units("") == []

    def test_single_paragraph_returned_as_one_unit(self):
        text = "Just one paragraph with several words."
        units = _split_into_units(text)
        assert len(units) == 1

    def test_large_paragraph_split_into_sentences(self):
        # Construct a paragraph of 90 words — should trigger sentence splitting
        long_para = ". ".join(["word " * 10 for _ in range(9)]) + "."
        units = _split_into_units(long_para)
        assert len(units) > 1


# ---------------------------------------------------------------------------
# SentenceWindowChunker
# ---------------------------------------------------------------------------

class TestSentenceWindowChunkerInit:
    def test_invalid_overlap_equal_to_size_raises(self):
        with pytest.raises(ValueError, match="chunk_overlap"):
            SentenceWindowChunker(chunk_size=10, chunk_overlap=10)

    def test_invalid_overlap_greater_than_size_raises(self):
        with pytest.raises(ValueError):
            SentenceWindowChunker(chunk_size=10, chunk_overlap=15)


class TestSentenceWindowChunker:
    @pytest.fixture
    def chunker(self) -> SentenceWindowChunker:
        return SentenceWindowChunker(chunk_size=100, chunk_overlap=20)

    def test_short_document_produces_one_chunk(self, chunker):
        doc = make_document("A very short document.")
        chunks = chunker.chunk(doc)
        assert len(chunks) == 1

    def test_empty_document_produces_no_chunks(self, chunker):
        doc = make_document("")
        chunks = chunker.chunk(doc)
        assert chunks == []

    def test_long_article_produces_multiple_chunks(self):
        parser = MarkdownParser()
        doc = parser.parse(FIXTURES / "long_article.md")
        chunker = SentenceWindowChunker(chunk_size=100, chunk_overlap=20)
        chunks = chunker.chunk(doc)
        assert len(chunks) > 1

    def test_all_chunks_have_non_empty_content(self, chunker):
        parser = MarkdownParser()
        doc = parser.parse(FIXTURES / "simple.md")
        chunks = chunker.chunk(doc)
        assert all(c.content.strip() for c in chunks)

    def test_chunks_have_64_char_content_hash(self, chunker):
        doc = make_document("Some content to hash deterministically.")
        chunks = chunker.chunk(doc)
        for chunk in chunks:
            assert len(chunk.content_hash) == 64  # SHA-256 hex digest

    def test_chunk_ids_are_stable_across_calls(self, chunker):
        doc = make_document("Stable content for identity test.")
        ids_first = [c.id for c in chunker.chunk(doc)]
        ids_second = [c.id for c in chunker.chunk(doc)]
        assert ids_first == ids_second

    def test_content_hash_is_deterministic(self, chunker):
        doc = make_document("Deterministic hashing test.")
        hash_a = chunker.chunk(doc)[0].content_hash
        hash_b = chunker.chunk(doc)[0].content_hash
        assert hash_a == hash_b

    def test_heading_context_preserved_in_metadata(self, chunker):
        sections = [Section(heading="Introduction", level=1, content="Intro text here.")]
        doc = make_document("Intro text here.", sections=sections)
        chunks = chunker.chunk(doc)
        assert chunks[0].metadata["heading"] == "Introduction"

    def test_source_path_preserved_on_all_chunks(self):
        path = Path("my_notes/topic.md")
        doc = make_document("Some content.", path=path)
        chunker = SentenceWindowChunker()
        chunks = chunker.chunk(doc)
        assert all(c.source_path == path for c in chunks)

    def test_chunk_indices_are_sequential_from_zero(self):
        parser = MarkdownParser()
        doc = parser.parse(FIXTURES / "long_article.md")
        chunker = SentenceWindowChunker(chunk_size=100, chunk_overlap=20)
        chunks = chunker.chunk(doc)
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    def test_section_boundaries_respected(self, chunker):
        sections = [
            Section(heading="Part A", level=1, content="Alpha beta gamma delta."),
            Section(heading="Part B", level=1, content="Epsilon zeta eta theta."),
        ]
        doc = make_document(
            "Alpha beta gamma delta. Epsilon zeta eta theta.",
            sections=sections,
        )
        chunks = chunker.chunk(doc)
        headings = {c.metadata["heading"] for c in chunks}
        assert "Part A" in headings
        assert "Part B" in headings

    def test_word_count_in_metadata_matches_content(self, chunker):
        doc = make_document("One two three four five.")
        chunks = chunker.chunk(doc)
        for chunk in chunks:
            assert chunk.metadata["word_count"] == _word_count(chunk.content)

    def test_chunk_id_contains_source_stem(self):
        path = Path("notes/my_topic.md")
        doc = make_document("Content.", path=path)
        chunker = SentenceWindowChunker()
        chunks = chunker.chunk(doc)
        assert all(c.id.startswith("my_topic:") for c in chunks)
