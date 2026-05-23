"""OllamaEmbedder: generates vector embeddings via a local Ollama instance.

Conforms to the ``EmbeddingProvider`` Protocol defined in ``interfaces.py``.
All configuration is sourced from ``Settings``; no values are hardcoded.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import ollama

if TYPE_CHECKING:
    from knowledge_onboarding_agent.config import Settings


class OllamaEmbedder:
    """Calls the Ollama embed API to produce float-vector embeddings.

    Texts are sent in batches of *batch_size* to respect the 16 GB memory
    budget on the target machine (see runtime-constraints.md).

    Raises:
        ollama.ResponseError: if the model is not available or Ollama returns
            a non-200 response.
        httpx.ConnectError / httpx.RemoteProtocolError: if the Ollama daemon
            is not reachable at *base_url*.
    """

    def __init__(self, model: str, base_url: str, batch_size: int = 32) -> None:
        self._model = model
        self._batch_size = batch_size
        self._client = ollama.Client(host=base_url)

    @classmethod
    def from_settings(cls, settings: Settings) -> OllamaEmbedder:
        """Construct an ``OllamaEmbedder`` from a ``Settings`` object."""
        return cls(
            model=settings.embeddings.model,
            base_url=settings.embeddings.ollama_base_url,
            batch_size=settings.embeddings.batch_size,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed *texts* and return one float vector per input text.

        Sends requests in batches of *batch_size*. The returned list preserves
        the same order as the input.

        Args:
            texts: Non-empty strings to embed.  Empty input returns ``[]``.

        Returns:
            A list of float vectors, one per input text.
        """
        if not texts:
            return []

        vectors: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            response = self._client.embed(model=self._model, input=batch)
            vectors.extend(response.embeddings)
        return vectors
