"""Configuração do logging estruturado com structlog."""

from __future__ import annotations

import logging
import sys

import structlog

_configurado = False


def setup_logging(level: str = "INFO", verbose: bool = False) -> None:
    """Configura o logging estruturado.

    Args:
        level: Nível de log (DEBUG, INFO, WARNING, ERROR).
        verbose: Se True, usa console renderer colorido; se False, JSON.
    """
    global _configurado
    if _configurado:
        return

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if verbose:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
    _configurado = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Retorna um logger estruturado.

    Inicializa a configuração padrão se ainda não estiver configurado.
    """
    if not _configurado:
        setup_logging()
    return structlog.get_logger(name)