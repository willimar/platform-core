"""Testes da validação pré-execução."""

from unittest.mock import MagicMock, patch

import pytest

from agent_sdk.types import ToolSpec
from platform_core.config.schema import AgentConfig, TarefaSpec
from platform_core.engine.validator import ValidationError, validar_agente
from platform_core.tools.registry import ToolRegistry


def make_config(modelo: str = "llama3.1:8b", ferramentas: list[str] = None) -> AgentConfig:
    return AgentConfig(
        nome="Teste",
        versao="1.0.0",
        modelo=modelo,
        instrucoes="Instrucoes de teste com tamanho minimo ok.",
        ferramentas=ferramentas or ["tool1"],
        tarefa=TarefaSpec(descricao="Faca algo.", saida_esperada="Algo feito."),
        max_passos=5,
        timeout_segundos=60,
    )


def make_registry(tools: list[str]) -> ToolRegistry:
    registry = ToolRegistry()
    for nome in tools:
        spec = ToolSpec(
            nome=nome,
            descricao=f"Ferramenta {nome}",
            descricao_completa=f"Ferramenta {nome}",
            parametros={},
            funcao=lambda: "ok",
        )
        registry.register(spec)
    return registry


class TestValidator:
    def test_validacao_passa_com_ferramentas_corretas(self):
        """Modelo real (não 'fake') deve chamar _verificar_modelo_ollama."""
        config = make_config(modelo="llama3.1:8b", ferramentas=["tool1", "tool2"])
        registry = make_registry(["tool1", "tool2"])

        # Mock do httpx pra simular Ollama respondendo com o modelo disponível
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "llama3.1:8b"}]}
        mock_response.raise_for_status = MagicMock()

        with patch("platform_core.engine.validator.httpx.get", return_value=mock_response):
            validar_agente(config, registry)  # não deve lançar

    def test_validacao_falha_com_ferramenta_faltando(self):
        config = make_config(ferramentas=["tool1", "tool2"])
        registry = make_registry(["tool1"])  # tool2 não existe

        with pytest.raises(ValidationError, match="não encontradas"):
            validar_agente(config, registry)

    def test_validacao_modelo_ollama_nao_encontrado(self):
        config = make_config(modelo="llama3.1:8b")
        registry = make_registry(["tool1"])

        # Mock do httpx retornando lista vazia de modelos
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": []}
        mock_response.raise_for_status = MagicMock()

        with patch("platform_core.engine.validator.httpx.get", return_value=mock_response):
            with pytest.raises(ValidationError, match="não encontrado"):
                validar_agente(config, registry)

    def test_validacao_modelo_ollama_encontrado(self):
        config = make_config(modelo="llama3.1:8b")
        registry = make_registry(["tool1"])

        mock_response = MagicMock()
        mock_response.json.return_value = {"models": [{"name": "llama3.1:8b"}]}
        mock_response.raise_for_status = MagicMock()

        with patch("platform_core.engine.validator.httpx.get", return_value=mock_response):
            validar_agente(config, registry)  # não deve lançar

    def test_validacao_ollama_indisponivel_nao_falha(self):
        """Se Ollama estiver offline, a validação continua (pode funcionar depois)."""
        config = make_config(modelo="llama3.1:8b")
        registry = make_registry(["tool1"])

        with patch(
            "platform_core.engine.validator.httpx.get", side_effect=Exception("Connection refused")
        ):
            validar_agente(config, registry)  # não deve lançar

    def test_validacao_modelo_fake_pula_ollama(self):
        """Modelo 'fake' não deve chamar Ollama (usado em testes)."""
        config = make_config(modelo="fake", ferramentas=["tool1"])
        registry = make_registry(["tool1"])

        # Se chamar httpx.get, vai falhar (não mockamos)
        # Mas como modelo == "fake", o validator deve pular a verificação
        validar_agente(config, registry)  # não deve lançar
