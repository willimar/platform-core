"""Testes do loader de agent.yaml."""

import pytest

from platform_core.config.loader import AgentLoadError, load_agent


class TestLoader:
    def test_carrega_yaml_valido(self, tmp_path):
        yaml_content = """
nome: "Teste Agente"
versao: "1.0.0"
modelo: "llama3.1:8b"
instrucoes: "Você é um agente de teste que responde perguntas."
ferramentas:
  - test_tool
tarefa:
  descricao: "Responda a pergunta."
  saida_esperada: "Resposta direta."
"""
        arquivo = tmp_path / "agent.yaml"
        arquivo.write_text(yaml_content, encoding="utf-8")

        config = load_agent(arquivo)
        assert config.nome == "Teste Agente"
        assert config.versao == "1.0.0"
        assert "test_tool" in config.ferramentas

    def test_erro_arquivo_inexistente(self, tmp_path):
        with pytest.raises(AgentLoadError, match="não encontrado"):
            load_agent(tmp_path / "nao_existe.yaml")

    def test_erro_versao_invalida(self, tmp_path):
        yaml_content = """
nome: "Teste"
versao: "versao-ruim"
modelo: "llama"
instrucoes: "Instruções de teste para validar o schema."
ferramentas:
  - test
tarefa:
  descricao: "Descrição mínima válida."
  saida_esperada: "Saída esperada válida."
"""
        arquivo = tmp_path / "agent.yaml"
        arquivo.write_text(yaml_content, encoding="utf-8")
        with pytest.raises(AgentLoadError, match="SemVer"):
            load_agent(arquivo)

    def test_erro_ferramentas_vazias(self, tmp_path):
        yaml_content = """
nome: "Teste"
versao: "1.0.0"
modelo: "llama"
instrucoes: "Instruções válidas com mínimo de dez caracteres."
ferramentas: []
tarefa:
  descricao: "Descrição mínima válida."
  saida_esperada: "Saída esperada válida."
"""
        arquivo = tmp_path / "agent.yaml"
        arquivo.write_text(yaml_content, encoding="utf-8")
        with pytest.raises(AgentLoadError):
            load_agent(arquivo)
