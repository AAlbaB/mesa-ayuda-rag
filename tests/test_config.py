"""Pruebas de carga y validación de configuración (T-22)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.config import Settings


def _base_env(**overrides) -> dict:
    """Entorno mínimo válido para instanciar Settings en pruebas.

    _env_file=None evita que Pydantic Settings lea el .env del proyecto,
    que contaminaría los valores de los campos y ocultaría errores de validación.
    """
    base = {
        "telegram_bot_token": "test_token_123",
        "llm_api_key": "sk-test-key",
        "_env_file": None,
    }
    base.update(overrides)
    return base


class TestSettingsDefaults:
    def test_defaults_applied(self):
        s = Settings(**_base_env())
        assert s.llm_provider == "openai"
        assert s.llm_model == "gpt-4o-mini"
        assert s.chunk_size == 800
        assert s.chunk_overlap == 100
        assert s.retrieval_top_k == 4
        assert s.similarity_threshold == 0.30
        assert s.history_length == 10
        assert s.rate_limit_per_minute == 10
        assert s.log_level == "INFO"
        assert s.allowed_user_ids == []
        assert s.admin_user_ids == []

    def test_required_missing_telegram_token(self):
        with pytest.raises(ValidationError) as exc_info:
            Settings(llm_api_key="sk-test", _env_file=None)
        assert "telegram_bot_token" in str(exc_info.value)

    def test_required_missing_llm_api_key(self):
        with pytest.raises(ValidationError) as exc_info:
            Settings(telegram_bot_token="token123", _env_file=None)
        assert "llm_api_key" in str(exc_info.value)


class TestIntListParsing:
    def test_comma_separated_string(self):
        s = Settings(**_base_env(allowed_user_ids="111,222,333"))
        assert s.allowed_user_ids == [111, 222, 333]

    def test_single_id(self):
        s = Settings(**_base_env(admin_user_ids="999"))
        assert s.admin_user_ids == [999]

    def test_empty_string_gives_empty_list(self):
        s = Settings(**_base_env(allowed_user_ids=""))
        assert s.allowed_user_ids == []

    def test_list_passthrough(self):
        s = Settings(**_base_env(allowed_user_ids=[42, 43]))
        assert s.allowed_user_ids == [42, 43]


class TestValidators:
    def test_invalid_llm_provider(self):
        with pytest.raises(ValidationError):
            Settings(**_base_env(llm_provider="cohere"))

    def test_valid_providers(self):
        for provider in ("openai", "anthropic", "google"):
            s = Settings(**_base_env(llm_provider=provider))
            assert s.llm_provider == provider

    def test_log_level_normalized_to_upper(self):
        s = Settings(**_base_env(log_level="debug"))
        assert s.log_level == "DEBUG"

    def test_invalid_log_level(self):
        with pytest.raises(ValidationError):
            Settings(**_base_env(log_level="VERBOSE"))

    def test_chunk_overlap_must_be_less_than_chunk_size(self):
        with pytest.raises(ValidationError):
            Settings(**_base_env(chunk_size=100, chunk_overlap=100))

    def test_valid_chunk_overlap(self):
        s = Settings(**_base_env(chunk_size=800, chunk_overlap=50))
        assert s.chunk_overlap == 50
