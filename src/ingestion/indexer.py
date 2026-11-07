"""Gestión del índice vectorial con ChromaDB persistente.

Los imports de sentence-transformers y chromadb son lazy (dentro de los métodos)
para que las pruebas unitarias puedan importar este módulo sin descargar torch/chromadb.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.documents import Document

if TYPE_CHECKING:
    from langchain_community.vectorstores import Chroma

logger = logging.getLogger(__name__)

# Nombre de la colección dentro de ChromaDB
_COLLECTION_NAME = "knowledge_base"
# Archivo que registra el estado de indexación para RF-09 (indexación incremental)
_STATE_FILENAME = "index_state.json"


class VectorIndexer:
    """Envuelve ChromaDB para ingesta, persistencia y consulta del índice vectorial."""

    def __init__(self, vector_store_path: Path, embedding_model: str) -> None:
        self._store_path = vector_store_path
        self._state_path = vector_store_path / _STATE_FILENAME
        self._embedding_model = embedding_model  # lazy: se instancia al primer uso
        self._store: Chroma | None = None

    def _get_embeddings(self):  # noqa: ANN201
        from langchain_community.embeddings import HuggingFaceEmbeddings  # lazy
        if not hasattr(self, "_embeddings_obj"):
            self._embeddings_obj = HuggingFaceEmbeddings(model_name=self._embedding_model)
        return self._embeddings_obj

    def _make_chroma(self, persist_directory: str) -> Chroma:
        from langchain_community.vectorstores import Chroma as _Chroma  # lazy
        # hnsw:space=cosine garantiza que similarity_search_with_relevance_scores
        # devuelva valores en [0, 1] en lugar de distancias L2 negativas.
        return _Chroma(
            collection_name=_COLLECTION_NAME,
            embedding_function=self._get_embeddings(),
            persist_directory=persist_directory,
            collection_metadata={"hnsw:space": "cosine"},
        )

    # ── API pública ───────────────────────────────────────────────────────────

    def load_or_create(self) -> None:
        """Carga el índice desde disco si existe; lo crea vacío en caso contrario."""
        self._store = self._make_chroma(str(self._store_path))
        count = self._store._collection.count()
        logger.info("Índice cargado con %d fragmentos", count)

    def build_index(
        self,
        chunks: list[Document],
        *,
        incremental: bool = False,
    ) -> int:
        """Indexa *chunks* en ChromaDB.

        Args:
            chunks: fragmentos con metadatos (source, page, chunk_index, file_type).
            incremental: si True, elimina fragmentos anteriores del mismo archivo
                         antes de reinsertar (RF-09). Si False, vacía el índice completo.

        Returns:
            Número de chunks indexados.
        """
        if self._store is None:
            self.load_or_create()

        if not chunks:
            logger.info("No hay chunks para indexar")
            return 0

        if incremental:
            sources = {c.metadata["source"] for c in chunks}
            self._delete_by_sources(sources)
        else:
            # Reinicia el índice completo
            self._store.delete_collection()  # type: ignore[union-attr]
            self._store = self._make_chroma(str(self._store_path))

        self._store.add_documents(chunks)  # type: ignore[union-attr]
        logger.info("Indexados %d fragmentos", len(chunks))
        return len(chunks)

    def get_indexed_sources(self) -> list[str]:
        """Retorna los nombres de archivo únicos presentes en el índice."""
        if self._store is None:
            return []
        result = self._store._collection.get(include=["metadatas"])
        sources = {m["source"] for m in result["metadatas"] if "source" in m}
        return sorted(sources)

    def get_store(self) -> Chroma:
        """Retorna el store subyacente para usarlo en el retriever."""
        if self._store is None:
            self.load_or_create()
        return self._store  # type: ignore[return-value]

    # ── Indexación incremental (RF-09) ────────────────────────────────────────

    def load_index_state(self) -> dict[str, dict]:
        """Carga el estado de indexación (hash + timestamp por archivo)."""
        if not self._state_path.exists():
            return {}
        try:
            return json.loads(self._state_path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("No se pudo leer index_state.json; se reconstruirá")
            return {}

    def save_index_state(self, state: dict[str, dict]) -> None:
        """Persiste el estado de indexación en disco."""
        self._state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @staticmethod
    def file_md5(file_path: Path) -> str:
        """Calcula el MD5 de un archivo para detectar cambios (RF-09)."""
        h = hashlib.md5()
        h.update(file_path.read_bytes())
        return h.hexdigest()

    # ── Interno ───────────────────────────────────────────────────────────────

    def _delete_by_sources(self, sources: set[str]) -> None:
        """Elimina del índice todos los fragmentos de los archivos indicados."""
        for source in sources:
            results = self._store._collection.get(  # type: ignore[union-attr]
                where={"source": source},
                include=["metadatas"],
            )
            ids = results.get("ids", [])
            if ids:
                self._store._collection.delete(ids=ids)  # type: ignore[union-attr]
                logger.debug("Eliminados %d chunks de '%s'", len(ids), source)
