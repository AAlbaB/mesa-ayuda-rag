"""Pruebas de control de acceso y rate limiting (T-25)."""

from __future__ import annotations

import time

import pytest

from src.logging_setup import setup_logging
from src.security.access import AccessControl, RateLimiter

# Inicializa logging con clave de prueba para que hash_user_id funcione
setup_logging(level="ERROR", hash_key="test-key-for-unit-tests")


class TestAccessControl:
    @pytest.fixture
    def access(self):
        return AccessControl(allowed_ids=[100, 200], admin_ids=[999])

    def test_allowed_user_has_access(self, access):
        assert access.is_allowed(100) is True
        assert access.is_allowed(200) is True

    def test_unknown_user_denied(self, access):
        assert access.is_allowed(999_000) is False

    def test_admin_has_implicit_access(self, access):
        assert access.is_allowed(999) is True

    def test_admin_flag(self, access):
        assert access.is_admin(999) is True
        assert access.is_admin(100) is False

    def test_empty_allowed_denies_everyone(self):
        access = AccessControl(allowed_ids=[], admin_ids=[])
        assert access.is_allowed(42) is False

    def test_admin_not_in_allowed_still_has_access(self):
        access = AccessControl(allowed_ids=[1], admin_ids=[2])
        assert access.is_allowed(2) is True
        assert access.is_admin(2) is True


class TestRateLimiter:
    @pytest.fixture
    def limiter(self):
        return RateLimiter(max_per_minute=3)

    def test_first_messages_allowed(self, limiter):
        for _ in range(3):
            assert limiter.is_allowed(1) is True

    def test_exceeding_limit_denied(self, limiter):
        for _ in range(3):
            limiter.is_allowed(1)
        assert limiter.is_allowed(1) is False

    def test_different_users_independent(self, limiter):
        for _ in range(3):
            limiter.is_allowed(1)
        # Usuario 2 no debería verse afectado por el límite del usuario 1
        assert limiter.is_allowed(2) is True

    def test_window_resets_after_time(self, monkeypatch):
        """Simula que la ventana de 60 s expiró para el primer mensaje."""
        limiter = RateLimiter(max_per_minute=1)
        # Primer mensaje: OK
        assert limiter.is_allowed(1) is True
        # Segundo mensaje en el mismo segundo: bloqueado
        assert limiter.is_allowed(1) is False

        # Avanzamos el tiempo 61 s usando monkeypatch en time.monotonic
        original = time.monotonic
        monkeypatch.setattr(time, "monotonic", lambda: original() + 61)
        # Ahora la ventana se habrá limpiado
        assert limiter.is_allowed(1) is True
