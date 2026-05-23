"""Tests for knowledge_onboarding_agent.config — settings loading and validation."""

from pathlib import Path

import pytest

from knowledge_onboarding_agent.config import (
    Settings,
    load_settings,
)


class TestSettingsDefaults:
    def test_default_embedding_model(self):
        settings = Settings()
        assert settings.embeddings.model == "nomic-embed-text"

    def test_default_llm_model(self):
        settings = Settings()
        assert settings.llm.model == "mistral"

    def test_default_storage_backend(self):
        settings = Settings()
        assert settings.storage.backend == "chromadb"

    def test_default_retrieval_top_k(self):
        settings = Settings()
        assert settings.retrieval.top_k == 10
        assert settings.retrieval.top_k_scale_factor == 0.5

    def test_default_reranking_disabled(self):
        settings = Settings()
        assert settings.retrieval.reranking_enabled is False

    def test_default_chunk_size(self):
        settings = Settings()
        assert settings.ingestion.chunking.chunk_size == 512

    def test_default_watch_paths_empty(self):
        settings = Settings()
        assert settings.ingestion.watch_paths == []


class TestLoadSettings:
    def test_load_overrides_embedding_model(self, tmp_path: Path):
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(
            "embeddings:\n  model: mxbai-embed-large\n  batch_size: 16\n",
            encoding="utf-8",
        )
        settings = load_settings(config_path=config_file)
        assert settings.embeddings.model == "mxbai-embed-large"
        assert settings.embeddings.batch_size == 16

    def test_unspecified_values_fall_back_to_defaults(self, tmp_path: Path):
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(
            "embeddings:\n  model: mxbai-embed-large\n",
            encoding="utf-8",
        )
        settings = load_settings(config_path=config_file)
        # Only embedding model was overridden; everything else is default
        assert settings.llm.model == "mistral"
        assert settings.storage.backend == "chromadb"
        assert settings.retrieval.top_k == 10

    def test_empty_yaml_returns_all_defaults(self, tmp_path: Path):
        config_file = tmp_path / "settings.yaml"
        config_file.write_text("", encoding="utf-8")
        settings = load_settings(config_path=config_file)
        assert settings == Settings()

    def test_missing_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="settings.yaml"):
            load_settings(config_path=Path("/nonexistent/path/settings.yaml"))

    def test_load_from_project_config(self):
        """Smoke test: the real config/settings.yaml is valid and loadable."""
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config" / "settings.yaml"
        settings = load_settings(config_path=config_path)
        # The real config should still have sensible values
        assert settings.embeddings.model
        assert settings.llm.model
        assert settings.storage.backend in {"chromadb", "faiss"}
