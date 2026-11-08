"""Pipeline de ingesta: loader → chunker → indexer."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.ingestion.chunker import DocumentChunker
from src.ingestion.indexer import VectorIndexer
from src.ingestion.loader import load_documents

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx"}


@dataclass
class IngestionResult:
    """Resumen del proceso de ingesta."""

    processed: int
    failed: int
    total_chunks: int
    errors: list[str]


def run_ingestion(
    knowledge_base_path: Path,
    indexer: VectorIndexer,
    chunker: DocumentChunker,
    *,
    incremental: bool = False,
) -> IngestionResult:
    """Ejecuta el pipeline completo de ingesta.

    Con incremental=True implementa RF-09: solo procesa archivos nuevos
    o modificados comparando su MD5 con el estado guardado en index_state.json.
    """
    files_to_process, deleted_sources = _select_files(
        knowledge_base_path, indexer, incremental=incremental
    )

    # Purga chunks de archivos eliminados del disco y limpia su estado,
    # para que si se re-agregan con el mismo contenido se reindexen correctamente.
    if deleted_sources:
        logger.info("Purgando chunks de %d archivos eliminados: %s", len(deleted_sources), deleted_sources)
        indexer._delete_by_sources(deleted_sources)
        _remove_deleted_from_state(deleted_sources, indexer)

    if not files_to_process:
        logger.info("No hay archivos nuevos o modificados para indexar")
        return IngestionResult(processed=0, failed=0, total_chunks=0, errors=[])

    logger.info("Archivos a procesar: %d", len(files_to_process))

    docs, errors = load_documents(Path(str(knowledge_base_path)))
    failed_paths = set(errors)

    # Filtra solo los documentos de los archivos seleccionados
    if incremental:
        selected_names = {f.name for f in files_to_process}
        docs = [d for d in docs if d.metadata.get("source") in selected_names]

    chunks = chunker.split(docs)
    indexed = indexer.build_index(chunks, incremental=incremental)

    if incremental:
        _update_state(files_to_process, failed_paths, indexer)

    return IngestionResult(
        processed=len(files_to_process) - len(errors),
        failed=len(errors),
        total_chunks=indexed,
        errors=errors,
    )


def _select_files(
    knowledge_base_path: Path,
    indexer: VectorIndexer,
    *,
    incremental: bool,
) -> tuple[list[Path], set[str]]:
    """Retorna (archivos a procesar, nombres de archivos eliminados del disco).

    En modo incremental detecta:
    - Archivos nuevos o modificados (MD5 diferente) → reindexar.
    - Archivos que estaban en el índice pero ya no existen en disco → purgar.
    """
    if not knowledge_base_path.exists():
        return [], set()

    all_files = [
        f
        for f in knowledge_base_path.iterdir()
        if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTENSIONS
    ]

    if not incremental:
        return all_files, set()

    state = indexer.load_index_state()
    all_file_names = {f.name for f in all_files}

    # Archivos indexados previamente que ya no están en disco
    indexed_sources = set(indexer.get_indexed_sources())
    deleted_sources = indexed_sources - all_file_names

    changed = []
    for f in all_files:
        md5 = VectorIndexer.file_md5(f)
        saved = state.get(str(f), {})
        # Reindexar si el MD5 cambió O si los chunks ya no están en ChromaDB.
        # La segunda condición auto-sana el estado cuando index_state.json y
        # ChromaDB se desincronizaron (ej. archivo eliminado con código antiguo
        # que no limpiaba el estado, o volumen de ChromaDB recreado).
        if saved.get("md5") != md5 or f.name not in indexed_sources:
            changed.append(f)

    return changed, deleted_sources


def _update_state(
    files: list[Path],
    failed_paths: set[str],
    indexer: VectorIndexer,
) -> None:
    """Actualiza index_state.json; excluye archivos que fallaron al cargar."""
    state = indexer.load_index_state()
    now = datetime.now(timezone.utc).isoformat()
    for f in files:
        if str(f) not in failed_paths:
            state[str(f)] = {
                "md5": VectorIndexer.file_md5(f),
                "indexed_at": now,
            }
    indexer.save_index_state(state)


def _remove_deleted_from_state(deleted_names: set[str], indexer: VectorIndexer) -> None:
    """Elimina de index_state.json las entradas de archivos borrados del disco.

    Las claves del estado son rutas absolutas; deleted_names contiene solo nombres
    de archivo. Se hace match por nombre para limpiar la entrada correcta.
    Sin esta limpieza, si el archivo se re-agrega con el mismo contenido su MD5
    coincide con el estado guardado y no se detecta como nuevo → no se reindexia.
    """
    state = indexer.load_index_state()
    keys_to_remove = [k for k in state if Path(k).name in deleted_names]
    if keys_to_remove:
        for k in keys_to_remove:
            del state[k]
        indexer.save_index_state(state)
        logger.debug("Eliminadas %d entradas de index_state.json: %s", len(keys_to_remove), keys_to_remove)
