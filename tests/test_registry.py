"""Testes do ToolRegistry."""

import pytest

from agent_sdk import ToolExecutionError, clear_registry, tool
from platform_core.tools.registry import ToolRegistry


@pytest.fixture(autouse=True)
def limpar_registry_global():
    clear_registry()
    yield
    clear_registry()


class TestToolRegistry:
    def test_carrega_de_decorators(self):
        @tool("test_tool_1")
        def t1():
            """Ferramenta de teste."""
            return "ok"

        registry = ToolRegistry()
        count = registry.register_from_global()
        assert count == 1
        assert registry.has("test_tool_1")

    def test_execute_retorna_resultado(self):
        @tool("test_exec")
        def soma(a: int, b: int) -> int:
            """Soma dois números."""
            return a + b

        registry = ToolRegistry()
        registry.register_from_global()
        result = registry.execute("test_exec", {"a": 2, "b": 3})
        assert result.nome == "test_exec"
        assert result.resultado.sucesso is True
        # O registry converte tipos não-str/não-dict para string
        assert result.resultado.dados == "5"

    def test_execute_tool_execution_error(self):
        @tool("test_erro")
        def falha():
            """Ferramenta que falha."""
            raise ToolExecutionError("algo deu errado", retry=True)

        registry = ToolRegistry()
        registry.register_from_global()
        result = registry.execute("test_erro", {})
        assert result.resultado.sucesso is False
        assert "algo deu errado" in result.resultado.erro

    def test_execute_excecao_nao_tratada(self):
        @tool("test_excecao")
        def quebrar():
            """Ferramenta que lança exceção genérica."""
            raise ValueError("quebrou!")

        registry = ToolRegistry()
        registry.register_from_global()
        result = registry.execute("test_excecao", {})
        assert result.resultado.sucesso is False
        assert "ValueError" in result.resultado.erro

    def test_execute_ferramenta_inexistente(self):
        registry = ToolRegistry()
        with pytest.raises(KeyError):
            registry.execute("nao_existe", {})

    def test_list_names(self):
        @tool("test_a")
        def a():
            """A."""
            pass

        @tool("test_b")
        def b():
            """B."""
            pass

        registry = ToolRegistry()
        registry.register_from_global()
        assert set(registry.list_names()) == {"test_a", "test_b"}

    def test_to_prompt_text(self):
        @tool("test_prompt")
        def listar(qtd: int = 5):
            """Lista itens."""
            pass

        registry = ToolRegistry()
        registry.register_from_global()
        texto = registry.to_prompt_text()
        assert "test_prompt" in texto
        assert "Lista itens" in texto
