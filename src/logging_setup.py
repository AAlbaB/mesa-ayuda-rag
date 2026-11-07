"""Configuración de logging estructurado en JSON para toda la aplicación."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any


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


def setup_logging(level: str = "INFO") -> None:
    """Inicializa el sistema de logging con salida JSON a stderr.

    Debe llamarse una sola vez al arrancar la aplicación, antes de importar
    cualquier otro módulo que use logging.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(_JSONFormatter())
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)

    # Silencia loggers muy verbosos de librerías de terceros
    for noisy in ("httpx", "httpcore", "chromadb.telemetry"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def hash_user_id(user_id: int) -> str:
    """Retorna un HMAC-SHA256 truncado del user_id para logs sin exponer el ID real.

    Usa LOG_HASH_KEY del entorno como clave para evitar ataques de fuerza bruta
    por enumeración (los IDs de Telegram son numéricos y tienen rango acotado).
    Si la clave no está configurada, usa una cadena fija de advertencia — suficiente
    para pruebas, inseguro en producción.
    """
    key = os.environ.get("LOG_HASH_KEY", "INSECURE-dev-key-change-in-prod").encode()
    mac = hmac.new(key, str(user_id).encode(), hashlib.sha256)
    return mac.hexdigest()[:16]
