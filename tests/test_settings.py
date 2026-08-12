"""Testes das configurações globais."""

import pytest

from platform_core.config.settings import Settings, get_settings, reset_settings


@pytest.fixture(autouse=True)
def _limpa_settings():
    """Reseta settings entre testes."""
    reset_settings()
    yield
    reset_settings()


class TestSettings:
    def test_defaults(self):
        settings = Settings()
        assert settings.ollama_base_url == "http://localhost:11434"
        assert settings.log_level == "INFO"
        assert settings.max_retries == 2

    def test_env_vars(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom:8080")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("MAX_RETRIES", "5")

        settings = Settings()
        assert settings.ollama_base_url == "http://custom:8080"
        assert settings.log_level == "DEBUG"
        assert settings.max_retries == 5

    def test_log_level_invalido(self):
        with pytest.raises(ValueError, match="LOG_LEVEL inválido"):
            Settings(log_level="INVALID")

    def test_max_retries_negativo(self):
        with pytest.raises(ValueError, match="MAX_RETRIES deve ser >= 0"):
            Settings(max_retries=-1)

    def test_get_settings_singleton(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_reset_settings(self):
        s1 = get_settings()
        reset_settings()
        s2 = get_settings()
        assert s1 is not s2
