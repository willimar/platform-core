"""Configuração do logging estruturado com structlog."""

from __future__ import annotations

import logging

import structlog

from platform_core.config.settings import get_settings

_configurado = False
_log_file_handle = None


def setup_logging(verbose: bool = False) -> None:
    """Configura o logging estruturado.

    Logs vão para dois sinks simultaneamente:
    - stderr (console): JSON ou colorido (se verbose)
    - arquivo (logs/platform.log): sempre JSON

    Args:
        verbose: Se True, usa console renderer colorido; se False, JSON.
    """
    global _configurado, _log_file_handle
    if _configurado:
        return

    settings = get_settings()
    level = "DEBUG" if verbose else settings.log_level

    # Cria diretório de logs e abre o arquivo com line buffering (autoflush)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    log_file = settings.log_dir / "platform.log"
    _log_file_handle = open(log_file, "a", encoding="utf-8", buffering=1)

    # Processors comuns
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # Renderers separados pra cada sink
    file_renderer = structlog.processors.JSONRenderer()
    if verbose:
        console_renderer = structlog.dev.ConsoleRenderer()
    else:
        console_renderer = structlog.processors.JSONRenderer()

    def write_to_file(logger, method_name, event_dict):
        """Escreve JSON no arquivo e devolve o event_dict pro próximo processor."""
        rendered = file_renderer(logger, method_name, event_dict)
        _log_file_handle.write(rendered + "\n")
        return event_dict  # dict intacto, não string

    def render_for_console(logger, method_name, event_dict):
        """ÚLTIMO processor: devolve STRING pro PrintLogger."""
        return console_renderer(logger, method_name, event_dict)

    structlog.configure(
        processors=processors + [write_to_file, render_for_console],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level, logging.INFO)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

    _configurado = True

    # Log de bootstrap
    get_logger(__name__).info(
        "logging_configurado",
        level=level,
        log_file=str(log_file),
    )


def get_logger(name: str):
    """Retorna um logger estruturado."""
    if not _configurado:
        setup_logging()
    return structlog.get_logger(name)
