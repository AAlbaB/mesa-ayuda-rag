"""Handlers del bot de Telegram: comandos y mensajes de texto."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.history import ConversationHistory
from src.ingestion.chunker import DocumentChunker
from src.ingestion.indexer import VectorIndexer
from src.ingestion.pipeline import IngestionResult, run_ingestion
from src.llm.chain import RAGChain
from src.logging_setup import hash_user_id
from src.retrieval.retriever import RAGRetriever
from src.security.access import AccessControl, RateLimiter
from src.security.sanitizer import sanitize_input

logger = logging.getLogger(__name__)

# Caracteres iniciales que los lectores de CSV interpretan como fórmulas
_CSV_FORMULA_CHARS = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_csv_cell(value: str) -> str:
    """Neutraliza valores que podrían interpretarse como fórmulas en hojas de cálculo."""
    if value and value[0] in _CSV_FORMULA_CHARS:
        return "'" + value
    return value


_DENIED_MSG = "⛔ No tienes acceso a este asistente. Contacta con el administrador."
_RATE_MSG = "⏳ Demasiados mensajes. Espera un momento antes de continuar."
_ERROR_MSG = "❌ Ocurrió un error al procesar tu mensaje. Inténtalo de nuevo en unos segundos."
_EMPTY_MSG = "Por favor envía un mensaje de texto con tu pregunta."


class BotHandlers:
    """Agrupa todos los handlers del bot y mantiene las dependencias en un solo lugar."""

    def __init__(
        self,
        access_control: AccessControl,
        rate_limiter: RateLimiter,
        retriever: RAGRetriever,
        chain: RAGChain,
        history: ConversationHistory,
        indexer: VectorIndexer,
        chunker: DocumentChunker,
        knowledge_base_path: Path,
        unanswered_log_path: Path,
    ) -> None:
        self._access = access_control
        self._rate = rate_limiter
        self._retriever = retriever
        self._chain = chain
        self._history = history
        self._indexer = indexer
        self._chunker = chunker
        self._kb_path = knowledge_base_path
        self._unanswered_path = unanswered_log_path

    # ── Middleware ────────────────────────────────────────────────────────────

    def _check_access(self, user_id: int) -> bool:
        """Retorna False y registra intento si el usuario no está autorizado."""
        if not self._access.is_allowed(user_id):
            logger.warning("Acceso denegado", extra={"user_id_hash": hash_user_id(user_id)})
            return False
        return True

    def _check_rate(self, user_id: int) -> bool:
        """Retorna False si el usuario excedió el rate limit."""
        return self._rate.is_allowed(user_id)

    # ── Comandos (RF-06) ──────────────────────────────────────────────────────

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id  # type: ignore[union-attr]
        if not self._check_access(user_id):
            await update.message.reply_text(_DENIED_MSG)  # type: ignore[union-attr]
            return

        await update.message.reply_text(  # type: ignore[union-attr]
            "👋 ¡Hola! Soy el asistente de mesa de ayuda.\n\n"
            "Puedo responder preguntas sobre las políticas internas de la organización "
            "basándome en los documentos disponibles.\n\n"
            "Comandos disponibles:\n"
            "• /help — ayuda y lista de comandos\n"
            "• /fuentes — documentos indexados\n"
            "• /reset — borrar historial de conversación\n\n"
            "Escribe tu pregunta y te respondo. 📄"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id  # type: ignore[union-attr]
        if not self._check_access(user_id):
            await update.message.reply_text(_DENIED_MSG)  # type: ignore[union-attr]
            return

        is_admin = self._access.is_admin(user_id)
        admin_section = "\n• /reindex — reindexar documentos (solo admins)" if is_admin else ""

        await update.message.reply_text(  # type: ignore[union-attr]
            "📖 *Comandos disponibles:*\n\n"
            "• /start — mensaje de bienvenida\n"
            "• /help — esta ayuda\n"
            "• /fuentes — lista de documentos indexados\n"
            "• /reset — borra tu historial de conversación"
            f"{admin_section}\n\n"
            "Simplemente escribe tu pregunta para obtener una respuesta.",
            parse_mode="Markdown",
        )

    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id  # type: ignore[union-attr]
        if not self._check_access(user_id):
            await update.message.reply_text(_DENIED_MSG)  # type: ignore[union-attr]
            return

        self._history.reset(user_id)
        await update.message.reply_text("✅ Historial de conversación borrado.")  # type: ignore[union-attr]

    async def fuentes(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = update.effective_user.id  # type: ignore[union-attr]
        if not self._check_access(user_id):
            await update.message.reply_text(_DENIED_MSG)  # type: ignore[union-attr]
            return

        sources = self._indexer.get_indexed_sources()
        if not sources:
            await update.message.reply_text(  # type: ignore[union-attr]
                "⚠️ No hay documentos indexados actualmente."
            )
            return

        lines = "\n".join(f"• {s}" for s in sources)
        await update.message.reply_text(f"📂 *Documentos disponibles:*\n\n{lines}", parse_mode="Markdown")  # type: ignore[union-attr]

    async def reindex(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Reindexación manual restringida a admins (RF-08)."""
        user_id = update.effective_user.id  # type: ignore[union-attr]
        if not self._check_access(user_id):
            await update.message.reply_text(_DENIED_MSG)  # type: ignore[union-attr]
            return
        if not self._access.is_admin(user_id):
            await update.message.reply_text("⛔ Este comando es solo para administradores.")  # type: ignore[union-attr]
            return

        await update.message.reply_text("🔄 Reindexando documentos, por favor espera...")  # type: ignore[union-attr]

        try:
            result: IngestionResult = run_ingestion(
                self._kb_path,
                self._indexer,
                self._chunker,
                incremental=True,
            )
        except Exception:
            logger.exception("Error durante reindexación")
            await update.message.reply_text("❌ Error durante la reindexación. Revisa los logs.")  # type: ignore[union-attr]
            return

        msg = (
            f"✅ Reindexación completada:\n"
            f"• Procesados: {result.processed}\n"
            f"• Fragmentos totales: {result.total_chunks}\n"
            f"• Errores: {result.failed}"
        )
        if result.errors:
            msg += "\n\nArchivos con error:\n" + "\n".join(f"  - {e}" for e in result.errors)

        await update.message.reply_text(msg)  # type: ignore[union-attr]

    # ── Mensaje de texto (pipeline RAG) ──────────────────────────────────────

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Procesa un mensaje de texto: acceso → rate limit → RAG → respuesta."""
        user_id = update.effective_user.id  # type: ignore[union-attr]
        uid_hash = hash_user_id(user_id)

        if not self._check_access(user_id):
            await update.message.reply_text(_DENIED_MSG)  # type: ignore[union-attr]
            return

        if not self._check_rate(user_id):
            await update.message.reply_text(_RATE_MSG)  # type: ignore[union-attr]
            return

        raw_text = update.message.text or ""  # type: ignore[union-attr]
        if not raw_text.strip():
            await update.message.reply_text(_EMPTY_MSG)  # type: ignore[union-attr]
            return

        query = sanitize_input(raw_text)
        if not query:
            await update.message.reply_text(_EMPTY_MSG)  # type: ignore[union-attr]
            return

        logger.info("Consulta recibida", extra={"user_id_hash": uid_hash, "query_len": len(query)})

        try:
            chunks = self._retriever.retrieve(query)
            history = self._history.get(user_id)
            answer, sources = self._chain.run(query, chunks, history)
        except Exception:
            logger.exception("Error en pipeline RAG", extra={"user_id_hash": uid_hash})
            await update.message.reply_text(_ERROR_MSG)  # type: ignore[union-attr]
            return

        # Registra preguntas sin respuesta (RF-10)
        if not chunks:
            self._log_unanswered(uid_hash, query)

        self._history.add(user_id, "user", query)
        self._history.add(user_id, "assistant", answer)

        # Formatea respuesta con fuentes
        if sources:
            full_response = f"{answer}\n\n📄 *Fuentes:* {', '.join(sources)}"
        else:
            full_response = answer

        await update.message.reply_text(full_response, parse_mode="Markdown")  # type: ignore[union-attr]

    # ── Log de preguntas sin respuesta (RF-10) ────────────────────────────────

    def _log_unanswered(self, uid_hash: str, query: str) -> None:
        """Registra la pregunta en CSV con timestamp y hash del user_id."""
        from datetime import datetime, timezone

        try:
            is_new = not self._unanswered_path.exists()
            with self._unanswered_path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                if is_new:
                    writer.writerow(["timestamp", "user_id_hash", "query"])
                writer.writerow([
                    datetime.now(timezone.utc).isoformat(),
                    uid_hash,
                    _sanitize_csv_cell(query),
                ])
        except Exception:
            logger.exception("No se pudo registrar pregunta sin respuesta")
