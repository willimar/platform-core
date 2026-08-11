"""Testes do logging estruturado."""

import time
from pathlib import Path

import pytest

from platform_core.config import settings as settings_module
from platform_core.logging import structured as structured_module
from platform_core.logging.structured import get_logger, setup_logging


@pytest.fixture(autouse=True)
def _limpa(tmp_path, monkeypatch):
    """Usa um diretório temporário pra logs e reseta caches globais."""
    settings_module.reset_settings()
    structured_module._configurado = False
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    yield
    settings_module.reset_settings()
    structured_module._configurado = False


class TestLogging:
    def test_log_cria_arquivo(self, tmp_path):
        setup_logging(verbose=False)
        logger = get_logger("test")
        logger.info("mensagem_teste", chave="valor")

        # Pequeno delay + flush pra garantir escrita em disco
        time.sleep(0.05)

        log_file = tmp_path / "platform.log"
        assert log_file.exists()
        conteudo = log_file.read_text(encoding="utf-8")
        assert "mensagem_teste" in conteudo
        assert "chave" in conteudo
        assert "valor" in conteudo