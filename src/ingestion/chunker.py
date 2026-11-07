"""Fragmentación de documentos en chunks con metadatos preservados."""

from __future__ import annotations

import logging

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class DocumentChunker:
    """Divide documentos en fragmentos de tamaño controlado.

    Usa RecursiveCharacterTextSplitter, que separa primero por párrafos,
    luego por frases, luego por palabras; respeta la estructura natural del texto.
    """

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            # Separadores en orden de preferencia (párrafo > línea > frase > palabra)
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def split(self, documents: list[Document]) -> list[Document]:
        """Fragmenta *documents* y agrega chunk_index a los metadatos de cada fragmento."""
        if not documents:
            return []

        chunks = self._splitter.split_documents(documents)

        # Numerar chunks por documento fuente para facilitar la citación
        source_counter: dict[str, int] = {}
        for chunk in chunks:
            source = chunk.metadata.get("source", "")
            idx = source_counter.get(source, 0)
            chunk.metadata["chunk_index"] = idx
            source_counter[source] = idx + 1

        logger.info(
            "Fragmentación completa",
            extra={"chunk_count": len(chunks), "source": "chunker"},
        )
        return chunks
