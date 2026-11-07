"""Gestión del historial conversacional por usuario en memoria (RF-05)."""

from __future__ import annotations

from collections import deque


class ConversationHistory:
    """Diccionario de historiales por user_id, con tamaño máximo configurable.

    El historial vive en memoria del proceso; se reinicia al reiniciar el bot
    (supuesto A-01 documentado en specs/spec.md).
    """

    def __init__(self, max_messages: int = 10) -> None:
        # max_messages se aplica al total de mensajes (user + assistant)
        self._max = max_messages
        self._data: dict[int, deque[dict[str, str]]] = {}

    def add(self, user_id: int, role: str, content: str) -> None:
        """Agrega un mensaje al historial del usuario, respetando el límite."""
        if user_id not in self._data:
            self._data[user_id] = deque(maxlen=self._max)
        self._data[user_id].append({"role": role, "content": content})

    def get(self, user_id: int) -> list[dict[str, str]]:
        """Retorna el historial del usuario como lista ordenada (más antiguo primero)."""
        return list(self._data.get(user_id, []))

    def reset(self, user_id: int) -> None:
        """Borra el historial del usuario (comando /reset, RF-06)."""
        self._data.pop(user_id, None)
