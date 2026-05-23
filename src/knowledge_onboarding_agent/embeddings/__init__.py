"""Embeddings stage: converts Chunk objects to vector representations via Ollama."""

from knowledge_onboarding_agent.embeddings.chunk_embedder import ChunkEmbedder
from knowledge_onboarding_agent.embeddings.ollama_embedder import OllamaEmbedder

__all__ = ["OllamaEmbedder", "ChunkEmbedder"]
