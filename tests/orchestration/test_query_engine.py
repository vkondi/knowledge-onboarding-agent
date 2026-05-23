"""Tests for QueryEngine.

Uses duck-typed fakes for Retriever and the Ollama LLM client so no live
Ollama instance or ChromaDB is required for unit tests.  Integration tests
that require Ollama are marked ``@pytest.mark.integration``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from knowledge_onboarding_agent.models import Chunk, RetrievedChunk, Response
from knowledge_onboarding_agent.orchestration.query_engine import QueryEngine


# ---------------------------------------------------------------------------
# Fake helpers
# ---------------------------------------------------------------------------

def _make_retrieved_chunk(
    content: str = "Sample content.",
    source_path: str = "notes.md",
    chunk_index: int = 0,
    score: float = 0.9,
    chunk_id: str | None = None,
) -> RetrievedChunk:
    cid = chunk_id or f"{Path(source_path).stem}:{chunk_index}"
    chunk = Chunk(
        id=cid,
        source_path=Path(source_path),
        content=content,
        chunk_index=chunk_index,
        metadata={},
        content_hash="abc123",
    )
    return RetrievedChunk(chunk=chunk, score=score)


class FakeRetriever:
    """Retriever duck-type that returns pre-canned results."""

    def __init__(self, results: list[RetrievedChunk] | None = None) -> None:
        self._results = results or []
        self.calls: list[str] = []

    def search(self, query: str) -> list[RetrievedChunk]:
        self.calls.append(query)
        return self._results


class FakeLLMClient:
    """ollama.Client duck-type that returns a fixed answer."""

    def __init__(self, answer: str = "Fake LLM answer.") -> None:
        self.answer = answer
        self.chats: list[dict] = []

    def chat(self, model: str, messages: list, options: dict | None = None) -> MagicMock:
        self.chats.append({"model": model, "messages": messages, "options": options})
        msg = MagicMock()
        msg.content = self.answer
        resp = MagicMock()
        resp.message = msg
        return resp


def _engine(
    results: list[RetrievedChunk] | None = None,
    answer: str = "Test answer.",
) -> tuple[QueryEngine, FakeRetriever, FakeLLMClient]:
    retriever = FakeRetriever(results)
    llm = FakeLLMClient(answer)
    engine = QueryEngine(
        retriever,
        llm_model="mistral",
        llm_base_url="http://localhost:11434",
        _llm_client=llm,
    )
    return engine, retriever, llm


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestQueryEngineInit:
    def test_from_settings_constructs_instance(self):
        from knowledge_onboarding_agent.config import load_settings
        settings = load_settings()
        retriever = FakeRetriever()
        engine = QueryEngine.from_settings(settings, retriever, _llm_client=FakeLLMClient())
        assert engine._model == settings.llm.model
        assert engine._temperature == settings.llm.temperature

    def test_from_settings_stores_context_window(self):
        from knowledge_onboarding_agent.config import load_settings
        settings = load_settings()
        retriever = FakeRetriever()
        engine = QueryEngine.from_settings(settings, retriever, _llm_client=FakeLLMClient())
        assert engine._context_window == settings.llm.context_window

    def test_model_name_stored(self):
        engine, _, _ = _engine()
        assert engine._model == "mistral"

    def test_default_context_window_is_8192(self):
        engine, _, _ = _engine()
        assert engine._context_window == 8192

    def test_custom_context_window_stored(self):
        retriever = FakeRetriever()
        llm = FakeLLMClient()
        engine = QueryEngine(
            retriever,
            llm_model="mistral",
            llm_base_url="http://localhost:11434",
            context_window=8192,
            _llm_client=llm,
        )
        assert engine._context_window == 8192


class TestQueryEngineNumCtx:
    """Verify that num_ctx is forwarded to the LLM client."""

    def test_num_ctx_passed_in_options(self):
        chunk = _make_retrieved_chunk(content="Context content.")
        engine, _, llm = _engine(results=[chunk])
        engine.ask("What is this?")
        assert llm.chats, "Expected at least one LLM call"
        options = llm.chats[0]["options"]
        assert "num_ctx" in options
        assert options["num_ctx"] == engine._context_window

    def test_custom_context_window_forwarded_to_llm(self):
        chunk = _make_retrieved_chunk(content="Context content.")
        retriever = FakeRetriever([chunk])
        llm = FakeLLMClient()
        engine = QueryEngine(
            retriever,
            llm_model="mistral",
            llm_base_url="http://localhost:11434",
            context_window=2048,
            _llm_client=llm,
        )
        engine.ask("What is this?")
        assert llm.chats[0]["options"]["num_ctx"] == 2048


# ---------------------------------------------------------------------------
# ask() — delegation and guard clauses
# ---------------------------------------------------------------------------

class TestQueryEngineAsk:
    def test_blank_question_returns_empty_answer(self):
        engine, retriever, llm = _engine()
        response = engine.ask("")
        assert response.answer == ""
        assert retriever.calls == []
        assert llm.chats == []

    def test_whitespace_question_returns_empty_answer(self):
        engine, _, _ = _engine()
        assert engine.ask("   ").answer == ""

    def test_empty_store_returns_no_info_message(self):
        engine, _, llm = _engine(results=[])
        response = engine.ask("What is onboarding?")
        assert "don't have enough information" in response.answer
        assert llm.chats == []

    def test_retriever_called_with_question(self):
        engine, retriever, _ = _engine([_make_retrieved_chunk()])
        engine.ask("What is onboarding?")
        assert retriever.calls == ["What is onboarding?"]

    def test_llm_called_once(self):
        engine, _, llm = _engine([_make_retrieved_chunk()])
        engine.ask("Any question?")
        assert len(llm.chats) == 1

    def test_llm_called_with_correct_model(self):
        engine, _, llm = _engine([_make_retrieved_chunk()])
        engine.ask("Any question?")
        assert llm.chats[0]["model"] == "mistral"

    def test_question_appears_in_prompt(self):
        engine, _, llm = _engine([_make_retrieved_chunk()])
        engine.ask("What is onboarding?")
        prompt_text = llm.chats[0]["messages"][0]["content"]
        assert "What is onboarding?" in prompt_text

    def test_chunk_content_appears_in_prompt(self):
        chunk_text = "Onboarding is a process for new hires."
        engine, _, llm = _engine([_make_retrieved_chunk(content=chunk_text)])
        engine.ask("question")
        prompt_text = llm.chats[0]["messages"][0]["content"]
        assert chunk_text in prompt_text

    def test_response_is_response_instance(self):
        engine, _, _ = _engine([_make_retrieved_chunk()])
        assert isinstance(engine.ask("q"), Response)

    def test_response_answer_is_llm_output(self):
        engine, _, _ = _engine([_make_retrieved_chunk()], answer="Specific answer.")
        assert engine.ask("q").answer == "Specific answer."

    def test_response_query_preserved(self):
        engine, _, _ = _engine([_make_retrieved_chunk()])
        response = engine.ask("What is onboarding?")
        assert response.query == "What is onboarding?"

    def test_response_sources_are_retrieved_chunks(self):
        chunks = [_make_retrieved_chunk(f"Content {i}", chunk_index=i) for i in range(3)]
        engine, _, _ = _engine(chunks)
        response = engine.ask("q")
        assert response.sources == chunks

    def test_temperature_passed_to_llm(self):
        retriever = FakeRetriever([_make_retrieved_chunk()])
        llm = FakeLLMClient()
        engine = QueryEngine(
            retriever,
            llm_model="mistral",
            llm_base_url="http://localhost:11434",
            temperature=0.05,
            _llm_client=llm,
        )
        engine.ask("q")
        assert llm.chats[0]["options"]["temperature"] == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# detect_conflicts()
# ---------------------------------------------------------------------------

class TestDetectConflicts:
    def test_single_source_returns_not_enough(self):
        engine, _, _ = _engine([_make_retrieved_chunk()])
        result = engine.detect_conflicts("topic")
        assert "Not enough sources" in result

    def test_zero_sources_returns_not_enough(self):
        engine, _, _ = _engine([])
        result = engine.detect_conflicts("topic")
        assert "Not enough sources" in result

    def test_two_sources_calls_llm(self):
        chunks = [
            _make_retrieved_chunk("Source A text.", source_path="a.md", chunk_index=0),
            _make_retrieved_chunk("Source B text.", source_path="b.md", chunk_index=0),
        ]
        engine, _, llm = _engine(chunks, answer="No contradictions found.")
        result = engine.detect_conflicts("topic")
        assert len(llm.chats) == 1
        assert result == "No contradictions found."

    def test_both_passages_appear_in_prompt(self):
        chunks = [
            _make_retrieved_chunk("Alpha content.", source_path="alpha.md"),
            _make_retrieved_chunk("Beta content.", source_path="beta.md"),
        ]
        engine, _, llm = _engine(chunks)
        engine.detect_conflicts("topic")
        prompt = llm.chats[0]["messages"][0]["content"]
        assert "Alpha content." in prompt
        assert "Beta content." in prompt

    def test_llm_called_with_zero_temperature(self):
        chunks = [_make_retrieved_chunk() for _ in range(2)]
        engine, _, llm = _engine(chunks)
        engine.detect_conflicts("topic")
        assert llm.chats[0]["options"]["temperature"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# generate_learning_path()
# ---------------------------------------------------------------------------

class TestGenerateLearningPath:
    def test_empty_store_returns_empty_list(self):
        engine, _, _ = _engine([])
        assert engine.generate_learning_path("topic") == []

    def test_returns_all_retrieved_chunks(self):
        chunks = [_make_retrieved_chunk(chunk_index=i) for i in range(4)]
        engine, _, _ = _engine(chunks)
        result = engine.generate_learning_path("topic")
        assert len(result) == 4

    def test_chunks_ordered_by_source_path_then_index(self):
        chunks = [
            _make_retrieved_chunk("C2", source_path="c.md", chunk_index=2),
            _make_retrieved_chunk("A0", source_path="a.md", chunk_index=0),
            _make_retrieved_chunk("C0", source_path="c.md", chunk_index=0),
            _make_retrieved_chunk("B1", source_path="b.md", chunk_index=1),
            _make_retrieved_chunk("A1", source_path="a.md", chunk_index=1),
        ]
        engine, _, _ = _engine(chunks)
        result = engine.generate_learning_path("topic")
        ids = [(str(r.chunk.source_path), r.chunk.chunk_index) for r in result]
        assert ids == [
            ("a.md", 0),
            ("a.md", 1),
            ("b.md", 1),
            ("c.md", 0),
            ("c.md", 2),
        ]

    def test_does_not_call_llm(self):
        chunks = [_make_retrieved_chunk() for _ in range(3)]
        engine, _, llm = _engine(chunks)
        engine.generate_learning_path("topic")
        assert llm.chats == []


# ---------------------------------------------------------------------------
# Integration tests (require Ollama running locally)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestQueryEngineIntegration:
    def test_ask_returns_non_empty_answer(self):
        import chromadb
        import hashlib
        import uuid

        from knowledge_onboarding_agent.config import load_settings
        from knowledge_onboarding_agent.embeddings.ollama_embedder import OllamaEmbedder
        from knowledge_onboarding_agent.models import EmbeddedChunk
        from knowledge_onboarding_agent.retrieval.semantic_search import SemanticSearch
        from knowledge_onboarding_agent.storage.chroma_store import ChromaDBStore

        settings = load_settings()
        embedder = OllamaEmbedder.from_settings(settings)
        store = ChromaDBStore(
            path=settings.storage.path,
            collection_name=f"test_qe_{uuid.uuid4().hex}",
            _client=chromadb.EphemeralClient(),
        )

        text = "New employees should complete their onboarding checklist on the first day."
        chunk = Chunk(
            id="doc:0",
            source_path=Path("onboarding.md"),
            content=text,
            chunk_index=0,
            metadata={"heading": "Onboarding"},
            content_hash=hashlib.sha256(text.encode()).hexdigest(),
        )
        vector = embedder.embed([text])[0]
        store.upsert_embedded_chunks([EmbeddedChunk(chunk=chunk, vector=vector)])

        retriever = SemanticSearch.from_settings(settings, embedder, store)
        engine = QueryEngine.from_settings(settings, retriever)

        response = engine.ask("What should new employees do on their first day?")
        assert isinstance(response.answer, str)
        assert len(response.answer) > 0
        assert len(response.sources) > 0
