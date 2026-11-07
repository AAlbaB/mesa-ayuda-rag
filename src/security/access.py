"""Control de acceso y rate limiting por user_id de Telegram."""

from __future__ import annotations

import logging
import time
from collections import deque

logger = logging.getLogger(__name__)


class AccessControl:
    """Verifica si un user_id está autorizado para usar el bot (RF-07)."""

    def __init__(self, allowed_ids: list[int], admin_ids: list[int]) -> None:
        # Los admins tienen acceso implícito
        self._allowed: frozenset[int] = frozenset(allowed_ids) | frozenset(admin_ids)
        self._admins: frozenset[int] = frozenset(admin_ids)

    def is_allowed(self, user_id: int) -> bool:
        """Retorna True si el usuario puede enviar mensajes al bot."""
        return user_id in self._allowed

    def is_admin(self, user_id: int) -> bool:
        """Retorna True si el usuario tiene permisos de administrador."""
        return user_id in self._admins


class RateLimiter:
    """Sliding window rate limiter en memoria por user_id.

    Registra los timestamps de los mensajes de cada usuario en una deque.
    Al consultar, descarta los timestamps fuera de la ventana de 60 s.
    No distribuido: se reinicia al reiniciar el bot (documentado en A-08).
    """

    def __init__(self, max_per_minute: int) -> None:
        self._limit = max_per_minute
        self._windows: dict[int, deque[float]] = {}

    def is_allowed(self, user_id: int) -> bool:
        """Registra el intento y retorna True si el usuario no excedió el límite."""
        now = time.monotonic()
        window_start = now - 60.0

        if user_id not in self._windows:
            self._windows[user_id] = deque()

        window = self._windows[user_id]

        # Elimina timestamps fuera de la ventana
        while window and window[0] < window_start:
            window.popleft()

        if len(window) >= self._limit:
            logger.debug("Rate limit excedido para user %s", user_id)
            return False

        window.append(now)
        return True
