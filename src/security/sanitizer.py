"""Sanitización de inputs de usuario para mitigar prompt injection (NF-03)."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Longitud máxima del mensaje antes de truncar (evita ataques de contexto largo)
_MAX_INPUT_LENGTH = 2000

# Patrones que caracterizan intentos comunes de prompt injection
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an|the)\s+\w+", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+are\s+)?(?:a|an|the)\s+\w+", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+)?(your\s+)?(previous\s+)?instructions?", re.IGNORECASE),
    re.compile(r"system\s*prompt|<system>|</?instructions?>", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"jailbreak|DAN\b|do\s+anything\s+now", re.IGNORECASE),
]


def sanitize_input(text: str) -> str:
    """Limpia el texto del usuario antes de enviarlo al pipeline RAG.

    Acciones:
    1. Trunca mensajes que superen _MAX_INPUT_LENGTH.
    2. Detecta y registra patrones de prompt injection conocidos.
       No bloquea el mensaje (el system prompt ya tiene la defensa de fondo),
       pero deja evidencia en el log para auditoría.

    Returns:
        Texto limpio listo para ser usado como query.
    """
    if not text or not text.strip():
        return ""

    cleaned = text.strip()

    if len(cleaned) > _MAX_INPUT_LENGTH:
        logger.warning(
            "Mensaje truncado de %d a %d caracteres",
            len(cleaned),
            _MAX_INPUT_LENGTH,
        )
        cleaned = cleaned[:_MAX_INPUT_LENGTH]

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(cleaned):
            logger.warning(
                "Posible intento de prompt injection detectado (patrón: %r)",
                pattern.pattern,
            )
            # El LLM tiene instrucciones explícitas de ignorar estas solicitudes;
            # registramos el intento pero pasamos el mensaje para no alertar al atacante.
            break

    return cleaned
