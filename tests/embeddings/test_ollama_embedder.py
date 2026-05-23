"""Tests for knowledge_onboarding_agent.embeddings.ollama_embedder.

Unit tests use a patched ollama.Client so no Ollama daemon is required.
Integration tests are marked @pytest.mark.integration and require a live
Ollama instance with nomic-embed-text available.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from knowledge_onboarding_agent.config import load_settings
from knowledge_onboarding_agent.embeddings.ollama_embedder import OllamaEmbedder

CONFIG_PATH = __import__("pathlib").Path(__file__).parent.parent.parent / "config" / "settings.yaml"

# A realistic embedding dimension for nomic-embed-text.
_DIM = 768


def _fake_embed_response(model, input) -> MagicMock:  # noqa: A002
    """Build a mock EmbedResponse whose .embeddings matches len(input)."""
    resp = MagicMock()
    resp.embeddings = [[0.1 * (i + 1)] * _DIM for i in range(len(input))]
    return resp


class TestOllamaEmbedderEmbed:
    @pytest.fixture
    def embedder(self) -> OllamaEmbedder:
        return OllamaEmbedder(
            model="nomic-embed-text",
            base_url="http://localhost:11434",
            batch_size=3,
        )

    def test_empty_input_returns_empty_list(self, embedder):
        assert embedder.embed([]) == []

    def test_returns_one_vector_per_text(self, embedder):
        with patch.object(embedder._client, "embed", side_effect=_fake_embed_response):
            result = embedder.embed(["hello", "world"])
        assert len(result) == 2

    def test_each_vector_has_expected_dimension(self, embedder):
        with patch.object(embedder._client, "embed", side_effect=_fake_embed_response):
            result = embedder.embed(["text"])
        assert len(result[0]) == _DIM

    def test_vectors_are_lists_of_float(self, embedder):
        with patch.object(embedder._client, "embed", side_effect=_fake_embed_response):
            result = embedder.embed(["one"])
        assert isinstance(result[0], list)
        assert isinstance(result[0][0], float)

    def test_batch_size_limits_single_api_call_size(self):
        """Embedder with batch_size=2 must split 5 texts into 3 calls."""
        embedder = OllamaEmbedder(
            model="nomic-embed-text",
            base_url="http://localhost:11434",
            batch_size=2,
        )
        call_sizes: list[int] = []

        def capturing_embed(model, input):  # noqa: A002
            call_sizes.append(len(input))
            return _fake_embed_response(model, input)

        with patch.object(embedder._client, "embed", side_effect=capturing_embed):
            result = embedder.embed(["a", "b", "c", "d", "e"])

        assert call_sizes == [2, 2, 1]
        assert len(result) == 5

    def test_output_order_preserved_across_batches(self):
        embedder = OllamaEmbedder(
            model="nomic-embed-text",
            base_url="http://localhost:11434",
            batch_size=2,
        )
        # Assign a unique first element to each vector so we can verify ordering.
        counter = {"n": 0}

        def ordered_embed(model, input):  # noqa: A002
            resp = MagicMock()
            resp.embeddings = [
                [float(counter["n"] + i)] + [0.0] * (_DIM - 1) for i in range(len(input))
            ]
            counter["n"] += len(input)
            return resp  # already correct — no change needed

        with patch.object(embedder._client, "embed", side_effect=ordered_embed):
            result = embedder.embed(["a", "b", "c", "d"])

        first_elements = [v[0] for v in result]
        assert first_elements == [0.0, 1.0, 2.0, 3.0]

    def test_single_text_no_batching_needed(self, embedder):
        with patch.object(embedder._client, "embed", side_effect=_fake_embed_response):
            result = embedder.embed(["single text"])
        assert len(result) == 1


class TestOllamaEmbedderFromSettings:
    def test_from_settings_constructs_instance(self):
        settings = load_settings(CONFIG_PATH)
        embedder = OllamaEmbedder.from_settings(settings)
        assert isinstance(embedder, OllamaEmbedder)

    def test_from_settings_uses_config_model(self):
        settings = load_settings(CONFIG_PATH)
        embedder = OllamaEmbedder.from_settings(settings)
        assert embedder._model == settings.embeddings.model

    def test_from_settings_uses_config_batch_size(self):
        settings = load_settings(CONFIG_PATH)
        embedder = OllamaEmbedder.from_settings(settings)
        assert embedder._batch_size == settings.embeddings.batch_size


@pytest.mark.integration
class TestOllamaEmbedderIntegration:
    """Requires a live Ollama daemon with nomic-embed-text pulled."""

    def test_embed_returns_non_empty_vectors(self):
        settings = load_settings(CONFIG_PATH)
        embedder = OllamaEmbedder.from_settings(settings)
        vectors = embedder.embed(["Knowledge Onboarding Agent embedding test."])
        assert len(vectors) == 1
        assert len(vectors[0]) > 0

    def test_embed_multiple_texts_returns_correct_count(self):
        settings = load_settings(CONFIG_PATH)
        embedder = OllamaEmbedder.from_settings(settings)
        texts = ["first sentence", "second sentence", "third sentence"]
        vectors = embedder.embed(texts)
        assert len(vectors) == len(texts)

    def test_different_texts_produce_different_vectors(self):
        settings = load_settings(CONFIG_PATH)
        embedder = OllamaEmbedder.from_settings(settings)
        v1, v2 = embedder.embed(["cats", "quantum computing"])
        assert v1 != v2

    def test_same_text_produces_same_vector(self):
        settings = load_settings(CONFIG_PATH)
        embedder = OllamaEmbedder.from_settings(settings)
        text = "deterministic embedding check"
        v1 = embedder.embed([text])[0]
        v2 = embedder.embed([text])[0]
        assert v1 == v2
