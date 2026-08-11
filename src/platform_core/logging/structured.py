"""Configuração do logging estruturado com structlog."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import structlog

from platform_core.config.settings import get_settings

_configurado = False


def setup_logging(verbose: bool = False) -> None:
    """Configura o logging estruturado.

    Args:
        verbose: Se True, usa console renderer colorido; se False, JSON.
    """
    global _configurado
    if _configurado:
        return

    settings = get_settings()
    level = "DEBUG" if verbose else settings.log_level

    # Cria o diretório de logs se não existir
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    log_file = settings.log_dir / "platform.log"

    # Processors comuns
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # Configura logging padrão (pra capturar logs de libs externas)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, level, logging.INFO),
    )

    # Handler de arquivo (JSON, rotação por tamanho)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(getattr(logging, level, logging.INFO))
    file_handler.setFormatter(logging.Formatter("%(message)s"))

    # Logger raiz
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)

    # Renderers
    if verbose:
        console_renderer = structlog.dev.ConsoleRenderer()
    else:
        console_renderer = structlog.processors.JSONRenderer()

    file_renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level, logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Formatter pro console
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=console_renderer,
    )
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Formatter pro arquivo
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processor=file_renderer,
    )
    file_handler.setFormatter(file_formatter)

    _configurado = True
    get_logger(__name__).info(
        "logging_configurado",
        level=level,
        log_file=str(log_file),
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Retorna um logger estruturado.

    Inicializa a configuração padrão se ainda não estiver configurado.
    """
    if not _configurado:
        setup_logging()
    return structlog.get_logger(name)