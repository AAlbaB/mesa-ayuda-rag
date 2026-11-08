"""Configuración de logging estructurado en JSON para toda la aplicación."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any

# Clave HMAC inicializada por setup_logging(); requerida antes de hash_user_id()
_HASH_KEY: bytes = b""


class _JSONFormatter(logging.Formatter):
    """Formateador que emite cada registro como una línea JSON.

    Campos garantizados: timestamp, level, module, event.
    Campos opcionales: user_id_hash (nunca el ID real), exception.
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "event": record.getMessage(),
        }

        # Propaga campos de contexto extra añadidos con logger.info("...", extra={...})
        for key in ("user_id_hash", "source", "chunk_count", "query_len"):
            if hasattr(record, key):
                entry[key] = getattr(record, key)

        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, ensure_ascii=False)


def setup_logging(level: str = "INFO", hash_key: str = "") -> None:
    """Inicializa el sistema de logging con salida JSON a stderr.

    Args:
        level: nivel de log (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        hash_key: clave HMAC para anonimizar user_ids. Si está vacía se
                  emite una advertencia y se usa una clave de desarrollo insegura.

    Debe llamarse una sola vez al arrancar la aplicación.
    """
    global _HASH_KEY

    handler = logging.StreamHandler()
    handler.setFormatter(_JSONFormatter())
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)

    # Silencia loggers muy verbosos de librerías de terceros
    for noisy in ("httpx", "httpcore", "chromadb.telemetry"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if hash_key:
        _HASH_KEY = hash_key.encode()
    else:
        _HASH_KEY = b"INSECURE-dev-key-change-in-prod"
        logging.warning(
            '{"event": "LOG_HASH_KEY no configurada — user_ids usan clave de desarrollo insegura"}'
        )


def hash_user_id(user_id: int) -> str:
    """Retorna un HMAC-SHA256 truncado del user_id para logs sin exponer el ID real.

    Requiere que setup_logging() haya sido llamada con un hash_key en producción.
    Los IDs de Telegram tienen rango acotado (numérico); sin clave HMAC son
    vulnerables a ataques de enumeración por rainbow table.
    """
    mac = hmac.new(_HASH_KEY, str(user_id).encode(), hashlib.sha256)
    return mac.hexdigest()[:16]
