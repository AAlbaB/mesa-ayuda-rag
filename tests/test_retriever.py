"""Pruebas del RAGRetriever con índice en memoria (T-24)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from src.retrieval.retriever import RAGRetriever, RetrievedChunk


def _make_chunk(content: str, source: str = "doc.pdf", page: int = 1) -> Document:
    return Document(
        page_content=content,
        metadata={"source": source, "page": page, "chunk_index": 0},
    )


@pytest.fixture
def mock_indexer():
    indexer = MagicMock()
    store = MagicMock()
    indexer.get_store.return_value = store
    return indexer, store


class TestRetrievedChunkFormatting:
    def test_format_source_with_page(self):
        doc = _make_chunk("contenido", source="politica.pdf", page=5)
        chunk = RetrievedChunk(document=doc, score=0.8)
        assert chunk.format_source() == "politica.pdf (pág. 5)"

    def test_format_source_without_page(self):
        doc = Document(
            page_content="contenido",
            metadata={"source": "readme.md", "page": -1, "chunk_index": 0},
        )
        chunk = RetrievedChunk(document=doc, score=0.7)
        assert chunk.format_source() == "readme.md"

    def test_content_property(self):
        doc = _make_chunk("texto de prueba")
        chunk = RetrievedChunk(document=doc, score=0.9)
        assert chunk.content == "texto de prueba"


class TestRetrieverThreshold:
    def test_chunks_above_threshold_returned(self, mock_indexer):
        indexer, store = mock_indexer
        doc = _make_chunk("vacaciones anuales son 15 días hábiles")
        store.similarity_search_with_relevance_scores.return_value = [(doc, 0.85)]

        retriever = RAGRetriever(indexer=indexer, top_k=4, similarity_threshold=0.30)
        results = retriever.retrieve("¿cuántos días de vacaciones hay?")

        assert len(results) == 1
        assert results[0].score == 0.85

    def test_chunks_below_threshold_filtered(self, mock_indexer):
        indexer, store = mock_indexer
        doc = _make_chunk("contenido irrelevante")
        store.similarity_search_with_relevance_scores.return_value = [(doc, 0.15)]

        retriever = RAGRetriever(indexer=indexer, top_k=4, similarity_threshold=0.30)
        results = retriever.retrieve("¿cuántos días de vacaciones?")

        assert results == []

    def test_mixed_scores_filtered_correctly(self, mock_indexer):
        indexer, store = mock_indexer
        docs = [
            (_make_chunk("relevante"), 0.75),
            (_make_chunk("poco relevante"), 0.20),
            (_make_chunk("moderadamente relevante"), 0.45),
        ]
        store.similarity_search_with_relevance_scores.return_value = docs

        retriever = RAGRetriever(indexer=indexer, top_k=4, similarity_threshold=0.30)
        results = retriever.retrieve("pregunta de prueba")

        assert len(results) == 2
        scores = [r.score for r in results]
        assert 0.75 in scores
        assert 0.45 in scores

    def test_empty_index_returns_empty_list(self, mock_indexer):
        indexer, store = mock_indexer
        store.similarity_search_with_relevance_scores.return_value = []

        retriever = RAGRetriever(indexer=indexer, top_k=4, similarity_threshold=0.30)
        results = retriever.retrieve("cualquier pregunta")

        assert results == []

    def test_top_k_passed_to_store(self, mock_indexer):
        indexer, store = mock_indexer
        store.similarity_search_with_relevance_scores.return_value = []

        retriever = RAGRetriever(indexer=indexer, top_k=6, similarity_threshold=0.30)
        retriever.retrieve("pregunta")

        store.similarity_search_with_relevance_scores.assert_called_once_with(
            "pregunta", k=6
        )
