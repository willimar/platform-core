"""Configurações globais da plataforma.

Carrega valores de variáveis de ambiente com defaults apropriados.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    """Configurações da plataforma.

    Attributes:
        ollama_base_url: URL base do Ollama.
        ollama_default_model: Modelo padrão se não especificado no YAML.
        log_level: Nível de log (DEBUG, INFO, WARNING, ERROR).
        log_dir: Diretório para logs em arquivo.
        max_retries: Retries padrão em caso de erro de ferramenta.
        request_timeout: Timeout padrão para chamadas HTTP (LLM, APIs).
    """

    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_default_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    )
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_dir: Path = field(default_factory=lambda: Path(os.getenv("LOG_DIR", "logs")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("MAX_RETRIES", "2")))
    request_timeout: float = field(
        default_factory=lambda: float(os.getenv("REQUEST_TIMEOUT", "120.0"))
    )

    def __post_init__(self):
        """Validações pós-inicialização."""
        if self.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            raise ValueError(
                f"LOG_LEVEL inválido: {self.log_level}. Use DEBUG, INFO, WARNING ou ERROR."
            )
        if self.max_retries < 0:
            raise ValueError(f"MAX_RETRIES deve ser >= 0, recebido: {self.max_retries}")
        if self.request_timeout <= 0:
            raise ValueError(f"REQUEST_TIMEOUT deve ser > 0, recebido: {self.request_timeout}")


# Instância global (singleton).
_settings: Settings | None = None


def get_settings() -> Settings:
    """Retorna a instância global de settings (cria se necessário)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reseta a instância global (usado apenas em testes)."""
    global _settings
    _settings = None
