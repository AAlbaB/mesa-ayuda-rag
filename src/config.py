"""Carga y validación centralizada de configuración desde variables de entorno."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración global del asistente, cargada desde .env.

    Falla rápido al arrancar si falta una variable requerida (marcada sin default).
    Las listas de IDs se pasan como cadenas separadas por coma:
        ALLOWED_USER_IDS=123456789,987654321
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Telegram ──────────────────────────────────────────────────────────────
    telegram_bot_token: str = Field(..., description="Token del bot (BotFather)")

    # ── LLM ───────────────────────────────────────────────────────────────────
    llm_provider: str = Field("openai", description="openai | anthropic | google")
    llm_model: str = Field("gpt-4o-mini")
    llm_api_key: str = Field(..., description="API key del proveedor LLM")
    llm_temperature: float = Field(0.1, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(512, gt=0)

    # ── Embeddings (local por defecto, sin segunda API key) ───────────────────
    embedding_provider: str = Field("huggingface")
    embedding_model: str = Field("paraphrase-multilingual-MiniLM-L12-v2")

    # ── Rutas ─────────────────────────────────────────────────────────────────
    knowledge_base_path: Path = Field(Path("knowledge_base"))
    vector_store_path: Path = Field(Path("chroma_db"))
    system_prompt_path: Path = Field(Path("prompts/system_prompt.md"))
    unanswered_log_path: Path = Field(Path("unanswered_questions.csv"))

    # ── Fragmentación ─────────────────────────────────────────────────────────
    chunk_size: int = Field(800, gt=0)
    chunk_overlap: int = Field(100, ge=0)

    # ── Recuperación ──────────────────────────────────────────────────────────
    retrieval_top_k: int = Field(4, gt=0)
    similarity_threshold: float = Field(0.30, ge=0.0, le=1.0)

    # ── Conversación ──────────────────────────────────────────────────────────
    history_length: int = Field(10, gt=0)

    # ── Control de acceso ─────────────────────────────────────────────────────
    allowed_user_ids: list[int] = Field(default_factory=list)
    admin_user_ids: list[int] = Field(default_factory=list)

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_limit_per_minute: int = Field(10, gt=0)

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = Field("INFO")

    # ── Validadores ───────────────────────────────────────────────────────────

    @field_validator("allowed_user_ids", "admin_user_ids", mode="before")
    @classmethod
    def _parse_int_list(cls, v: str | list) -> list[int]:
        """Convierte 'id1,id2,id3' a [id1, id2, id3]."""
        if isinstance(v, list):
            return v
        if isinstance(v, str) and v.strip():
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return []

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level debe ser uno de {valid}, recibido: {v!r}")
        return upper

    @field_validator("llm_provider")
    @classmethod
    def _validate_llm_provider(cls, v: str) -> str:
        valid = {"openai", "anthropic", "google"}
        lower = v.lower()
        if lower not in valid:
            raise ValueError(f"llm_provider debe ser uno de {valid}, recibido: {v!r}")
        return lower

    @field_validator("chunk_overlap")
    @classmethod
    def _overlap_less_than_size(cls, v: int, info) -> int:
        # info.data contiene los campos ya validados en orden de definición
        chunk_size = info.data.get("chunk_size", 800)
        if v >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({v}) debe ser menor que chunk_size ({chunk_size})"
            )
        return v


def get_settings() -> Settings:
    """Retorna la instancia global de configuración.

    Separar la instanciación en una función facilita el mock en pruebas.
    """
    return Settings()
