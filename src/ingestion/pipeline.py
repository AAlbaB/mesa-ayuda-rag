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

    # Purga chunks de archivos eliminados del disco
    if deleted_sources:
        logger.info("Purgando chunks de %d archivos eliminados: %s", len(deleted_sources), deleted_sources)
        indexer._delete_by_sources(deleted_sources)

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
        if saved.get("md5") != md5:
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
