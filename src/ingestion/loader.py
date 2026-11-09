"""Carga de documentos desde knowledge_base/ con extracción de metadatos."""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Extensiones soportadas mapeadas a su función de carga
_SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx"}


def load_documents(knowledge_base_path: Path) -> tuple[list[Document], list[str]]:
    """Carga todos los documentos soportados desde *knowledge_base_path*.

    Returns:
        docs: lista de Document con texto y metadatos (source, page, file_type).
        errors: lista de rutas de archivos que fallaron al cargar.
    """
    if not knowledge_base_path.exists():
        logger.warning("knowledge_base_path no existe: %s", knowledge_base_path)
        return [], []

    files = [
        f
        for f in knowledge_base_path.iterdir()
        if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTENSIONS
    ]

    if not files:
        logger.info("No se encontraron documentos en %s", knowledge_base_path)
        return [], []

    docs: list[Document] = []
    errors: list[str] = []

    for file_path in sorted(files):
        try:
            loaded = _load_single(file_path)
            docs.extend(loaded)
            logger.info(
                "Documento cargado",
                extra={"source": file_path.name, "chunk_count": len(loaded)},
            )
        except Exception:
            logger.exception("Error al cargar %s", file_path.name)
            errors.append(str(file_path))

    logger.info(
        "Carga completada: %d documentos, %d errores", len(files) - len(errors), len(errors)
    )
    return docs, errors


def _load_single(file_path: Path) -> list[Document]:
    """Carga un único archivo y retorna sus páginas/secciones como Documents."""
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        return _load_pdf(file_path)
    if ext in {".md", ".txt"}:
        return _load_text(file_path)
    if ext == ".docx":
        return _load_docx(file_path)

    raise ValueError(f"Extensión no soportada: {ext}")


def _load_pdf(file_path: Path) -> list[Document]:
    loader = PyPDFLoader(str(file_path))
    pages = loader.load()
    for i, doc in enumerate(pages):
        doc.metadata.update({
            "source": file_path.name,
            "page": doc.metadata.get("page", i),
            "file_type": "pdf",
        })
    return pages


def _load_text(file_path: Path) -> list[Document]:
    loader = TextLoader(str(file_path), encoding="utf-8")
    docs = loader.load()
    for doc in docs:
        doc.metadata.update({
            "source": file_path.name,
            "page": -1,
            "file_type": file_path.suffix.lstrip("."),
        })
    return docs


def _load_docx(file_path: Path) -> list[Document]:
    """Carga un .docx extrayendo el texto de todos los párrafos."""
    try:
        from docx import Document as DocxDocument  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "python-docx no está instalado. Instala las dependencias completas."
        ) from exc

    docx = DocxDocument(str(file_path))
    text = "\n\n".join(p.text for p in docx.paragraphs if p.text.strip())
    return [
        Document(
            page_content=text,
            metadata={"source": file_path.name, "page": -1, "file_type": "docx"},
        )
    ]
