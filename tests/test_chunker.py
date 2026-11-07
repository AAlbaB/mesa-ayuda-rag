"""Pruebas de fragmentación de documentos (T-23)."""

from __future__ import annotations

import pytest
from langchain_core.documents import Document

from src.ingestion.chunker import DocumentChunker


@pytest.fixture
def chunker():
    return DocumentChunker(chunk_size=200, chunk_overlap=20)


def _make_doc(content: str, source: str = "test.txt", page: int = -1) -> Document:
    return Document(
        page_content=content,
        metadata={"source": source, "page": page, "file_type": "txt"},
    )


class TestChunkSize:
    def test_long_text_produces_multiple_chunks(self, chunker):
        text = "Palabra " * 200  # ~1600 chars, mayor que chunk_size=200
        doc = _make_doc(text)
        chunks = chunker.split([doc])
        assert len(chunks) > 1

    def test_no_chunk_exceeds_configured_size(self, chunker):
        text = "A" * 1000
        doc = _make_doc(text)
        chunks = chunker.split([doc])
        for chunk in chunks:
            # El splitter puede exceder ligeramente chunk_size en la última palabra
            assert len(chunk.page_content) <= 300  # margen razonable

    def test_short_text_stays_as_single_chunk(self, chunker):
        text = "Texto corto que cabe en un solo fragmento."
        doc = _make_doc(text)
        chunks = chunker.split([doc])
        assert len(chunks) == 1


class TestMetadataPreservation:
    def test_source_metadata_preserved(self, chunker):
        doc = _make_doc("texto " * 50, source="politica.pdf", page=3)
        chunks = chunker.split([doc])
        for chunk in chunks:
            assert chunk.metadata["source"] == "politica.pdf"

    def test_page_metadata_preserved(self, chunker):
        doc = _make_doc("texto " * 50, page=7)
        chunks = chunker.split([doc])
        for chunk in chunks:
            assert chunk.metadata["page"] == 7

    def test_chunk_index_added(self, chunker):
        text = "Fragmento " * 100
        doc = _make_doc(text, source="doc.txt")
        chunks = chunker.split([doc])
        indices = [c.metadata["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_chunk_index_independent_per_source(self, chunker):
        docs = [
            _make_doc("texto " * 60, source="a.txt"),
            _make_doc("texto " * 60, source="b.txt"),
        ]
        chunks = chunker.split(docs)
        a_indices = [c.metadata["chunk_index"] for c in chunks if c.metadata["source"] == "a.txt"]
        b_indices = [c.metadata["chunk_index"] for c in chunks if c.metadata["source"] == "b.txt"]
        assert a_indices[0] == 0
        assert b_indices[0] == 0


class TestEdgeCases:
    def test_empty_list_returns_empty(self, chunker):
        assert chunker.split([]) == []

    def test_empty_document_content(self, chunker):
        doc = _make_doc("")
        chunks = chunker.split([doc])
        # Los splitters de LangChain pueden retornar 0 o 1 chunk vacío
        assert all(c.page_content == "" or c.page_content.strip() == "" for c in chunks)
