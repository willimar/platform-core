"""Configuração do logging estruturado com structlog."""

from __future__ import annotations

import logging

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

    # Cria o diretório de logs
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    log_file = settings.log_dir / "platform.log"

    # Abre o arquivo de log (append mode, autoflush via line_buffering)
    log_file_handle = open(log_file, "a", encoding="utf-8", buffering=1)

    # Renderers
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if verbose:
        console_renderer = structlog.dev.ConsoleRenderer()
    else:
        console_renderer = structlog.processors.JSONRenderer()

    file_renderer = structlog.processors.JSONRenderer()

    # Configura loggers separados: stderr (colorido ou JSON) e arquivo (sempre JSON)
    class DualWriter:
        """Escreve em dois sinks com renderers diferentes."""

        def __init__(self, console_out, file_out):
            self.console_out = console_out
            self.file_out = file_out

        def write(self, event_dict):
            # Console
            try:
                self.console_out(event_dict, None)
            except Exception:
                pass
            # Arquivo
            try:
                linha = file_renderer(None, None, event_dict)
                self.file_out.write(linha + "\n")
            except Exception:
                pass

        def flush(self):
            try:
                self.file_out.flush()
            except Exception:
                pass

    console_writer = console_renderer
    writer = DualWriter(console_writer, log_file_handle)

    structlog.configure(
        processors=processors
        + [
            lambda logger, method_name, event_dict: writer.write(event_dict) or event_dict,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level, logging.INFO)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

    _configurado = True

    # Log de bootstrap (depois de configurado)
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
