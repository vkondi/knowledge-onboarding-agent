"""Configuration loader for Knowledge Onboarding Agent.

Reads config/settings.yaml and validates it with Pydantic.
All runtime configuration is sourced from here — never hardcoded in stage modules.

Usage:
    from knowledge_onboarding_agent.config import load_settings

    settings = load_settings()
    model_name = settings.embeddings.model
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

# Default path: resolves to <project_root>/config/settings.yaml
_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "settings.yaml"


class ChunkingConfig(BaseModel):
    strategy: str = "sentence_window"
    chunk_size: int = 512
    chunk_overlap: int = 64


class IngestionConfig(BaseModel):
    watch_paths: list[str] = Field(default_factory=list)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)


class EmbeddingsConfig(BaseModel):
    model: str = "nomic-embed-text"
    batch_size: int = 32
    ollama_base_url: str = "http://localhost:11434"


class StorageConfig(BaseModel):
    backend: str = "chromadb"
    path: str = "./.knowledge-onboarding-agent/db"
    collection_name: str = "knowledge_base"


class RetrievalConfig(BaseModel):
    top_k: int = 10
    top_k_scale_factor: float = 0.5
    reranking_enabled: bool = False


class LLMConfig(BaseModel):
    model: str = "mistral"
    ollama_base_url: str = "http://localhost:11434"
    temperature: float = 0.1
    context_window: int = 8192


class Settings(BaseModel):
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)


def load_settings(config_path: Path = _DEFAULT_CONFIG_PATH) -> Settings:
    """Load and validate settings from a YAML config file.

    Args:
        config_path: Path to the settings.yaml file.
                     Defaults to <project_root>/config/settings.yaml.

    Returns:
        A fully validated Settings instance.

    Raises:
        FileNotFoundError: If the config file does not exist at the given path.
    """
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            "Ensure config/settings.yaml exists at the project root."
        )

    with config_path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    return Settings.model_validate(raw or {})
