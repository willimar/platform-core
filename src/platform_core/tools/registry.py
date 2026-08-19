"""Registry de ferramentas.

Descobre ferramentas registradas via @tool em módulos de agentes
e fornece execução segura com captura de erros.
"""

from __future__ import annotations

import importlib
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_sdk import ToolExecutionError, ToolResult, ToolSpec, get_registry
from platform_core.logging.structured import get_logger

logger = get_logger(__name__)


@dataclass
class ToolExecutionResult:
    """Resultado da execução de uma ferramenta pelo registry."""

    nome: str
    resultado: ToolResult
    duracao_ms: float


class ToolRegistry:
    """Registry de ferramentas disponíveis para um agente."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        """Registra uma ferramenta.

        Raises:
            ValueError: Se ferramenta com mesmo nome já estiver registrada.
        """
        if spec.nome in self._tools:
            raise ValueError(f"Ferramenta '{spec.nome}' já registrada")
        self._tools[spec.nome] = spec
        logger.info("ferramenta_registrada", nome=spec.nome)

    def register_from_global(self) -> int:
        """Registra todas as ferramentas do registry global do agent-sdk."""
        global_registry = get_registry()
        count = 0
        for spec in global_registry.values():
            if spec.nome not in self._tools:
                self._tools[spec.nome] = spec
                count += 1
        return count

    def load_from_module(self, module_name: str) -> int:
        """Carrega um módulo Python, disparando os decorators @tool."""
        logger.info("carregando_modulo", modulo=module_name)
        importlib.import_module(module_name)
        return self.register_from_global()

    def load_from_directory(self, directory: Path) -> int:
        """Carrega todos os módulos .py de um diretório como pacote.

        Adiciona o diretório-pai ao sys.path para que imports internos
        do agente (ex: from tools.auth import ...) funcionem.

        Args:
            directory: Diretório contendo módulos com ferramentas.

        Returns:
            Número total de ferramentas novas registradas.
        """
        directory = Path(directory).resolve()
        parent = directory.parent

        if not directory.exists():
            logger.warning("diretorio_nao_existe", diretorio=str(directory))
            return 0

        path_added = False
        if str(parent) not in sys.path:
            sys.path.insert(0, str(parent))
            path_added = True

        # Limpa cache de módulos com o mesmo nome (ex: "tools" de outro agente).
        # Sem isso, o segundo agente carregado no mesmo processo falha porque
        # sys.modules["tools"] ainda aponta pro primeiro diretório.
        nome_pacote = directory.name
        chaves_a_remover = [
            k for k in sys.modules
            if k == nome_pacote or k.startswith(f"{nome_pacote}.")
        ]
        for k in chaves_a_remover:
            logger.debug("removendo_modulo_cacheado", modulo=k)
            del sys.modules[k]

        count = 0
        try:
            for path in sorted(directory.glob("*.py")):
                if path.name.startswith("_"):
                    continue
                module_name = f"{directory.name}.{path.stem}"
                logger.info("carregando_modulo", modulo=module_name, path=str(path))
                importlib.import_module(module_name)
                count += self.register_from_global()
        finally:
            if path_added:
                sys.path.remove(str(parent))

        return count

    def get(self, nome: str) -> ToolSpec | None:
        """Retorna a spec de uma ferramenta por nome."""
        return self._tools.get(nome)

    def has(self, nome: str) -> bool:
        """Verifica se uma ferramenta está registrada."""
        return nome in self._tools

    def list_names(self) -> list[str]:
        """Lista os nomes de todas as ferramentas registradas."""
        return list(self._tools.keys())

    def list_specs(self) -> list[ToolSpec]:
        """Lista todas as specs registradas."""
        return list(self._tools.values())

    def execute(self, nome: str, parametros: dict[str, Any] | None = None) -> ToolExecutionResult:
        """Executa uma ferramenta com captura de erros.

        Raises:
            KeyError: Se ferramenta não estiver registrada.
        """
        spec = self._tools.get(nome)
        if spec is None:
            raise KeyError(f"Ferramenta '{nome}' não encontrada no registry")

        params = parametros or {}
        logger.info("executando_ferramenta", ferramenta=nome, parametros=params)

        inicio = time.perf_counter()
        try:
            resultado = spec.funcao(**params)
            duracao_ms = (time.perf_counter() - inicio) * 1000

            if isinstance(resultado, ToolResult):
                tool_result = resultado
            elif isinstance(resultado, (str, dict)):
                tool_result = ToolResult.ok(resultado, duracao_ms=duracao_ms)
            else:
                tool_result = ToolResult.ok(str(resultado), duracao_ms=duracao_ms)

            logger.info(
                "ferramenta_executada_ok",
                ferramenta=nome,
                duracao_ms=round(duracao_ms, 2),
            )
            return ToolExecutionResult(nome=nome, resultado=tool_result, duracao_ms=duracao_ms)

        except ToolExecutionError as e:
            duracao_ms = (time.perf_counter() - inicio) * 1000
            logger.warning(
                "ferramenta_erro_controlado",
                ferramenta=nome,
                erro=e.mensagem,
                retry=e.retry,
                duracao_ms=round(duracao_ms, 2),
            )
            return ToolExecutionResult(
                nome=nome,
                resultado=ToolResult.falha(e.mensagem, duracao_ms=duracao_ms, retry=e.retry),
                duracao_ms=duracao_ms,
            )

        except Exception as e:
            duracao_ms = (time.perf_counter() - inicio) * 1000
            logger.error(
                "ferramenta_excecao_nao_tratada",
                ferramenta=nome,
                erro=str(e),
                tipo_erro=type(e).__name__,
                duracao_ms=round(duracao_ms, 2),
            )
            return ToolExecutionResult(
                nome=nome,
                resultado=ToolResult.falha(
                    f"Erro inesperado: {type(e).__name__}: {e}",
                    duracao_ms=duracao_ms,
                ),
                duracao_ms=duracao_ms,
            )

    def to_prompt_text(self) -> str:
        """Gera a descrição de todas as ferramentas para o prompt do LLM."""
        if not self._tools:
            return "Nenhuma ferramenta disponível."
        linhas = [spec.to_prompt_text() for spec in self._tools.values()]
        return "\n".join(linhas)
