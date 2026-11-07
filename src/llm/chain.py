"""Cadena RAG: construye el prompt, llama al LLM y formatea la respuesta con fuentes."""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.retrieval.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

# Mensaje que el asistente devuelve cuando no hay contexto suficiente (RF-04)
_NO_INFO_MESSAGE = (
    "No tengo información sobre ese tema en los documentos disponibles. "
    "Te recomiendo consultar directamente con el área de Recursos Humanos o "
    "con el equipo de mesa de ayuda."
)


def build_llm(provider: str, model: str, api_key: str, temperature: float, max_tokens: int) -> BaseChatModel:
    """Instancia el LLM según el proveedor configurado.

    Permite cambiar de proveedor solo modificando LLM_PROVIDER en .env.
    """
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=api_key,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model_name=model,
            api_key=api_key,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )
    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
    raise ValueError(f"LLM_PROVIDER no soportado: {provider!r}. Usa openai, anthropic o google.")


class RAGChain:
    """Orquesta la generación de respuestas fundamentadas en los chunks recuperados."""

    def __init__(self, llm: BaseChatModel, system_prompt_path: Path) -> None:
        self._llm = llm
        self._system_prompt = self._load_system_prompt(system_prompt_path)

    def run(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        history: list[dict[str, str]],
    ) -> tuple[str, list[str]]:
        """Genera una respuesta a *query* usando *chunks* como contexto.

        Args:
            query: pregunta del usuario (ya sanitizada).
            chunks: fragmentos recuperados del índice. Lista vacía → RF-04.
            history: historial [{role, content}] más reciente del usuario.

        Returns:
            (respuesta_texto, fuentes) donde fuentes es la lista de citas únicas.
        """
        if not chunks:
            logger.info("Sin chunks relevantes → respuesta de desconocido (RF-04)")
            return _NO_INFO_MESSAGE, []

        context_block = self._build_context(chunks)
        messages = self._build_messages(query, context_block, history)

        try:
            response: AIMessage = self._llm.invoke(messages)
            answer = str(response.content).strip()
        except Exception:
            logger.exception("Error al llamar al LLM")
            raise

        sources = list({chunk.format_source() for chunk in chunks})
        return answer, sources

    # ── Internos ──────────────────────────────────────────────────────────────

    def _build_context(self, chunks: list[RetrievedChunk]) -> str:
        """Formatea los chunks como bloque de contexto para el prompt."""
        parts = []
        for i, chunk in enumerate(chunks, start=1):
            parts.append(
                f"[Fragmento {i} — Fuente: {chunk.format_source()}]\n{chunk.content}"
            )
        return "\n\n---\n\n".join(parts)

    def _build_messages(
        self,
        query: str,
        context_block: str,
        history: list[dict[str, str]],
    ) -> list:
        """Construye la lista de mensajes para la API del LLM.

        Estructura:
            SystemMessage(system_prompt)
            [HumanMessage / AIMessage del historial]
            HumanMessage(contexto + pregunta actual)
        """
        messages: list = [SystemMessage(content=self._system_prompt)]

        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

        user_turn = (
            f"Usa exclusivamente la siguiente información para responder.\n\n"
            f"=== INFORMACIÓN DISPONIBLE ===\n{context_block}\n\n"
            f"=== PREGUNTA ===\n{query}"
        )
        messages.append(HumanMessage(content=user_turn))
        return messages

    @staticmethod
    def _load_system_prompt(path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(
                f"Archivo de prompt de sistema no encontrado: {path}. "
                "Verifica SYSTEM_PROMPT_PATH en tu .env."
            )
        return path.read_text(encoding="utf-8")
