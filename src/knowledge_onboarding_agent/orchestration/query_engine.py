"""QueryEngine: coordinates retrieval and a local Ollama LLM to produce answers.

Conforms to the architecture described in docs/architecture/system-design.md.
Implements the following Orchestration sub-components in one class:
- QueryEngine          — RAG answer synthesis (ask)
- ConflictDetector     — flags contradictory claims across retrieved chunks
- LearningPathGenerator— orders retrieved chunks into a progressive reading sequence

The LLM is called via the ``ollama`` Python client (already used for embeddings),
keeping the dependency footprint minimal.  No external cloud APIs are used.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import ollama

from knowledge_onboarding_agent.models import Response, RetrievedChunk

if TYPE_CHECKING:
    from knowledge_onboarding_agent.config import Settings
    from knowledge_onboarding_agent.interfaces import Retriever

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_RAG_PROMPT = """\
You are a helpful knowledge assistant. Answer the question using ONLY the context provided below.
If the answer cannot be found in the context, respond with exactly:
"I don't have enough information to answer that."

Context:
{context}

Question: {question}

Answer:"""

_CONFLICT_PROMPT = """\
Review the following text passages from different sources.
Identify any factual contradictions between them.
If you find contradictions, describe each one clearly (e.g. "Source A says X, but Source B says Y").
If there are no contradictions, respond with exactly: "No contradictions found."

Passages:
{passages}"""


class QueryEngine:
    """RAG query engine that retrieves relevant chunks and synthesises an LLM answer.

    Parameters
    ----------
    retriever:
        Any ``Retriever`` implementation (e.g. ``SemanticSearch``).
    llm_model:
        Ollama model name for answer generation (e.g. ``"mistral"``).
    llm_base_url:
        Base URL of the local Ollama daemon.
    temperature:
        Sampling temperature for the LLM.  Lower = more deterministic.
    _llm_client:
        Injectable ``ollama.Client``-compatible object for testing.
        When ``None`` (default), a real ``ollama.Client`` is created.
    """

    def __init__(
        self,
        retriever: Retriever,
        *,
        llm_model: str,
        llm_base_url: str,
        temperature: float = 0.1,
        context_window: int = 8192,
        _llm_client: Any | None = None,
    ) -> None:
        self._retriever = retriever
        self._model = llm_model
        self._temperature = temperature
        self._context_window = context_window
        self._client: Any = _llm_client or ollama.Client(host=llm_base_url)

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        retriever: Retriever,
        *,
        _llm_client: Any | None = None,
    ) -> QueryEngine:
        """Construct a ``QueryEngine`` from a ``Settings`` object."""
        return cls(
            retriever=retriever,
            llm_model=settings.llm.model,
            llm_base_url=settings.llm.ollama_base_url,
            temperature=settings.llm.temperature,
            context_window=settings.llm.context_window,
            _llm_client=_llm_client,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def ask(self, question: str) -> Response:
        """Answer *question* using retrieved context and the local LLM.

        Returns a ``Response`` with the LLM answer and the source chunks used.
        When the store is empty or the question is blank, the answer field
        reflects that no information was found without making an LLM call.
        """
        if not question.strip():
            return Response(answer="", sources=[], query=question)

        retrieved = self._retriever.search(question)

        if not retrieved:
            return Response(
                answer="I don't have enough information to answer that.",
                sources=[],
                query=question,
            )

        context = self._format_context(retrieved)
        prompt = _RAG_PROMPT.format(context=context, question=question)
        answer = self._complete(prompt, temperature=self._temperature)
        return Response(answer=answer, sources=retrieved, query=question)

    def detect_conflicts(self, topic: str) -> str:
        """Retrieve chunks on *topic* and ask the LLM to identify contradictions.

        Returns a plain-text description of any contradictions found, or
        ``"No contradictions found."`` if there are none.
        Returns ``"Not enough sources to detect conflicts."`` when fewer than
        two chunks are retrieved.
        """
        retrieved = self._retriever.search(topic)
        if len(retrieved) < 2:
            return "Not enough sources to detect conflicts."

        passages = "\n\n".join(
            f"[{r.chunk.source_path.name}, chunk {r.chunk.chunk_index}]\n{r.chunk.content}"
            for r in retrieved
        )
        prompt = _CONFLICT_PROMPT.format(passages=passages)
        # Use temperature=0 for deterministic, factual comparison.
        return self._complete(prompt, temperature=0.0)

    def generate_learning_path(self, topic: str) -> list[RetrievedChunk]:
        """Return retrieved chunks ordered for progressive learning.

        Chunks are sorted by source file path (alphabetically) then by
        ``chunk_index`` within each document.  This groups each document's
        content together and preserves the author's intended reading order.

        Returns an empty list when no relevant chunks are found.
        """
        retrieved = self._retriever.search(topic)
        return sorted(
            retrieved,
            key=lambda r: (str(r.chunk.source_path), r.chunk.chunk_index),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _complete(self, prompt: str, *, temperature: float) -> str:
        """Send *prompt* to the Ollama LLM and return the response text."""
        response = self._client.chat(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": temperature, "num_ctx": self._context_window},
        )
        return response.message.content

    @staticmethod
    def _format_context(retrieved: list[RetrievedChunk]) -> str:
        """Format retrieved chunks as a numbered context block for the prompt."""
        parts = []
        for i, r in enumerate(retrieved, start=1):
            source_label = r.chunk.source_path.name
            parts.append(f"[{i}] {source_label}\n{r.chunk.content}")
        return "\n\n".join(parts)
