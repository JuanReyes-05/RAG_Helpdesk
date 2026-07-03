"""Configuración centralizada de logging estructurado con structlog.

Reglas:
- Toda la app (incluyendo logs de stdlib logging) se emite por el mismo
  renderer configurado aquí (JSON en prod, consola coloreada en dev).
- Los campos ligados vía structlog.contextvars.bind_contextvars() aparecen
  automáticamente en todos los eventos emitidos dentro de ese contexto
  (p. ej. request_id por request, consulta_id por /ask).
- Loggers ruidosos de librerías terceras se bajan a WARNING.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

_NOISY_LOGGERS = (
    "httpx",
    "httpcore",
    "openai",
    "urllib3",
    "chromadb",
    "chromadb.telemetry",
    "sentence_transformers",
    "transformers",
    "huggingface_hub",
    "watchfiles",
    "asyncio",
)


def setup_logging(level: str = "INFO", json_output: bool = False) -> None:
    """Configura structlog + stdlib logging con el mismo renderer.

    Parameters
    ----------
    level:
        Nivel mínimo (DEBUG/INFO/WARNING/ERROR).
    json_output:
        True → JSON por stdout (para Docker/prod/Loki/ELK).
        False → consola coloreada (dev local).
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    # Procesadores compartidos por logs de structlog y de stdlib logging.
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
    ]

    if json_output:
        # JSONRenderer necesita la excepción pre-formateada como string.
        shared_processors.append(structlog.processors.format_exc_info)
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        # ConsoleRenderer formatea las excepciones él mismo (pretty tracebacks).
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # 1) Configuración de structlog (loggers obtenidos vía structlog.get_logger).
    structlog.configure(
        processors=shared_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 2) Handler único para stdlib logging; usa el mismo renderer.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)

    # 3) Silenciar loggers ruidosos de terceros.
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Devuelve un logger estructurado. Preferir sobre logging.getLogger."""
    return structlog.get_logger(name)
