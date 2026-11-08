"""Punto de entrada del asistente de mesa de ayuda con RAG en Telegram."""

from __future__ import annotations

import logging
import sys

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from src.bot.handlers import BotHandlers
from src.bot.history import ConversationHistory
from src.config import get_settings
from src.ingestion.chunker import DocumentChunker
from src.ingestion.indexer import VectorIndexer
from src.ingestion.pipeline import run_ingestion
from src.llm.chain import RAGChain, build_llm
from src.logging_setup import setup_logging
from src.retrieval.retriever import RAGRetriever
from src.security.access import AccessControl, RateLimiter

logger = logging.getLogger(__name__)


def main() -> None:
    """Inicializa todos los componentes y arranca el bot en modo polling."""
    settings = get_settings()

    setup_logging(level=settings.log_level, hash_key=settings.log_hash_key)

    logger.info("Iniciando asistente de mesa de ayuda")

    # ── Ingesta e indexación ────────────────────────────────────────────────
    indexer = VectorIndexer(
        vector_store_path=settings.vector_store_path,
        embedding_model=settings.embedding_model,
    )
    indexer.load_or_create()

    chunker = DocumentChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    result = run_ingestion(
        knowledge_base_path=settings.knowledge_base_path,
        indexer=indexer,
        chunker=chunker,
        incremental=True,  # Solo procesa archivos nuevos/modificados (RF-09)
    )
    logger.info(
        "Ingesta completada",
        extra={"chunk_count": result.total_chunks, "source": "startup"},
    )

    if result.failed:
        logger.warning("Archivos con error de ingesta: %s", result.errors)

    # ── Retrieval y cadena RAG ──────────────────────────────────────────────
    retriever = RAGRetriever(
        indexer=indexer,
        top_k=settings.retrieval_top_k,
        similarity_threshold=settings.similarity_threshold,
    )

    try:
        llm = build_llm(
            provider=settings.llm_provider,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    except Exception:
        logger.exception("No se pudo instanciar el LLM — verifica LLM_PROVIDER y LLM_API_KEY")
        sys.exit(1)

    chain = RAGChain(llm=llm, system_prompt_path=settings.system_prompt_path)

    # ── Seguridad y estado conversacional ──────────────────────────────────
    access_control = AccessControl(
        allowed_ids=settings.allowed_user_ids,
        admin_ids=settings.admin_user_ids,
    )
    rate_limiter = RateLimiter(max_per_minute=settings.rate_limit_per_minute)
    history = ConversationHistory(max_messages=settings.history_length)

    # ── Handlers del bot ──────────────────────────────────────────────────
    handlers = BotHandlers(
        access_control=access_control,
        rate_limiter=rate_limiter,
        retriever=retriever,
        chain=chain,
        history=history,
        indexer=indexer,
        chunker=chunker,
        knowledge_base_path=settings.knowledge_base_path,
        unanswered_log_path=settings.unanswered_log_path,
    )

    # ── Aplicación de Telegram ────────────────────────────────────────────
    app = ApplicationBuilder().token(settings.telegram_bot_token).build()

    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help_command))
    app.add_handler(CommandHandler("reset", handlers.reset))
    app.add_handler(CommandHandler("fuentes", handlers.fuentes))
    app.add_handler(CommandHandler("reindex", handlers.reindex))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))

    logger.info("Bot iniciado en modo polling")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
