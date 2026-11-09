"""Búsqueda semántica sobre el índice vectorial con filtro por umbral de similitud."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from langchain_core.documents import Document

if TYPE_CHECKING:
    from src.ingestion.indexer import VectorIndexer

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """Fragmento recuperado del índice con su puntuación de similitud."""

    document: Document
    score: float

    @property
    def source(self) -> str:
        """Nombre de archivo del documento origen."""
        return self.document.metadata.get("source", "desconocido")

    @property
    def page(self) -> int:
        """Número de página; -1 si el formato no tiene páginas."""
        return self.document.metadata.get("page", -1)

    @property
    def content(self) -> str:
        """Texto del fragmento recuperado."""
        return self.document.page_content

    def format_source(self) -> str:
        """Retorna la cita de fuente formateada para incluir en la respuesta."""
        if self.page and self.page > 0:
            return f"{self.source} (pág. {self.page})"
        return self.source


class RAGRetriever:
    """Recupera fragmentos relevantes del índice vectorial dado una consulta."""

    def __init__(
        self,
        indexer: VectorIndexer,
        top_k: int = 4,
        similarity_threshold: float = 0.30,
    ) -> None:
        self._indexer = indexer
        self._top_k = top_k
        self._threshold = similarity_threshold

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        """Busca los fragmentos más similares a *query* en el índice.

        Returns:
            Lista de RetrievedChunk con score >= similarity_threshold,
            ordenados por similitud descendente. Lista vacía si no hay
            resultados sobre el umbral (activa RF-04).
        """
        store = self._indexer.get_store()

        # similarity_search_with_relevance_scores retorna (doc, score) donde
        # score=1.0 es similitud perfecta (distancia coseno convertida a [0, 1])
        results: list[tuple[Document, float]] = (
            store.similarity_search_with_relevance_scores(query, k=self._top_k)
        )

        chunks = [
            RetrievedChunk(document=doc, score=score)
            for doc, score in results
            if score >= self._threshold
        ]

        logger.debug(
            "Retrieval: %d candidatos, %d sobre umbral %.2f",
            len(results),
            len(chunks),
            self._threshold,
        )

        return chunks
