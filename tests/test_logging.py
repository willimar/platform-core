"""Testes do logging estruturado."""

from pathlib import Path

import pytest

from platform_core.config.settings import reset_settings
from platform_core.logging.structured import get_logger, setup_logging


@pytest.fixture(autouse=True)
def _limpa(tmp_path, monkeypatch):
    """Usa um diretório temporário pra logs."""
    reset_settings()
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    yield
    reset_settings()


class TestLogging:
    def test_log_cria_arquivo(self, tmp_path):
        setup_logging(verbose=False)
        logger = get_logger("test")
        logger.info("mensagem_teste", chave="valor")

        log_file = tmp_path / "platform.log"
        assert log_file.exists()
        conteudo = log_file.read_text(encoding="utf-8")
        assert "mensagem_teste" in conteudo
        assert "chave" in conteudo
        assert "valor" in conteudo