---
title: Getting Started with Retrieval-Augmented Generation
tags: [rag, ai, llm]
author: Notes
date: 2026-01-15
---

# Getting Started with Retrieval-Augmented Generation

Retrieval-Augmented Generation (RAG) is a technique that enhances large language
models by retrieving relevant context from an external knowledge base before
generating a response. It addresses the core limitation of LLMs: their knowledge
is frozen at training time.

## How It Works

A RAG system has three main components: a retriever, a knowledge base, and a
generator. The retriever embeds the user's query into a vector and searches the
knowledge base for semantically similar documents. The generator then uses both
the original query and the retrieved documents as context to produce an answer.

The knowledge base is typically a vector store - a database optimized for
approximate nearest-neighbor search over high-dimensional embedding vectors.

## Why Use RAG

RAG reduces hallucination by grounding the LLM's output in real documents from a
trusted knowledge base. The model can only claim what the retrieved documents
support, making it more reliable for domain-specific applications.

Additionally, the knowledge base can be updated independently of the model.
New documents are indexed without retraining, which is far more practical than
fine-tuning a new model each time information changes.

## Limitations

RAG is not a silver bullet. If the retriever returns irrelevant chunks, the LLM
will produce irrelevant or contradictory answers. The quality of retrieval is
directly tied to the quality of the embedding model and the chunking strategy.
