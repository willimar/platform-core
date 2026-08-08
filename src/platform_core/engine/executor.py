"""Executor de agentes — loop principal."""

from __future__ import annotations

import time
from typing import Any

from agent_sdk import ToolExecutionError

from platform_core.config.schema import AgentConfig
from platform_core.engine.state import AgentState, AgentStatus, Message
from platform_core.llm.client import LLMClient, LLMError
from platform_core.llm.parser import LLMParseError, parse_response
from platform_core.logging.structured import get_logger
from platform_core.tools.registry import ToolRegistry

logger = get_logger(__name__)


SYSTEM_PROMPT_TEMPLATE = """Você é o agente "{nome}".

## Instruções
{instrucoes}

## Tarefa
{tarefa_descricao}

## Formato de saída esperado
{tarefa_saida_esperada}

## Ferramentas disponíveis
{ferramentas_descricao}

## Regras de resposta
Responda SEMPRE em JSON válido, sem markdown code blocks:
- Para usar uma ferramenta:
  {{"acao": "usar_ferramenta", "ferramenta": "<nome>", "parametros": {{...}}}}
- Para finalizar:
  {{"acao": "finalizar", "resposta": "<texto final>"}}

Não invente ferramentas que não estão na lista.
Não responda fora do formato JSON.
"""


def montar_system_prompt(config: AgentConfig, registry: ToolRegistry) -> str:
    """Monta o system prompt a partir da config do agente.

    Args:
        config: Configuração do agente carregada do YAML.
        registry: Registry com as ferramentas disponíveis.

    Returns:
        System prompt completo.
    """
    ferramentas_descricao = registry.to_prompt_text()

    return SYSTEM_PROMPT_TEMPLATE.format(
        nome=config.nome,
        instrucoes=config.instrucoes,
        tarefa_descricao=config.tarefa.descricao,
        tarefa_saida_esperada=config.tarefa.saida_esperada,
        ferramentas_descricao=ferramentas_descricao,
    )


class Executor:
    """Executor de agentes.

    Gerencia o loop de raciocínio-ação: pergunta ao LLM, executa
    ferramentas, repete até finalizar ou atingir max_passos.

    Args:
        llm_client: Cliente de LLM (ex: OllamaClient).
        registry: Registry de ferramentas disponíveis.
        max_retries: Número máximo de retries em caso de erro de ferramenta.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        registry: ToolRegistry,
        max_retries: int = 2,
    ) -> None:
        self.llm_client = llm_client
        self.registry = registry
        self.max_retries = max_retries

    def executar(self, config: AgentConfig, entrada: str = "") -> AgentState:
        """Executa um agente completo.

        Args:
            config: Configuração do agente.
            entrada: Mensagem inicial do usuário (opcional).

        Returns:
            AgentState com o resultado final (status, resultado ou erro).
        """
        logger.info(
            "iniciando_execucao",
            agente=config.nome,
            versao=config.versao,
            modelo=config.modelo,
            max_passos=config.max_passos,
        )

        state = AgentState()
        state.status = AgentStatus.EM_EXECUCAO

        # Monta o system prompt e adiciona à conversa
        system_prompt = montar_system_prompt(config, self.registry)
        state.adicionar_mensagem("system", system_prompt)

        # Adiciona a mensagem do usuário (se houver) ou um prompt genérico
        user_message = entrada if entrada else config.tarefa.descricao
        state.adicionar_mensagem("user", user_message)

        inicio = time.perf_counter()

        try:
            while state.passo_atual < config.max_passos:
                state.passo_atual += 1
                logger.info(
                    "passo_iniciado",
                    passo=state.passo_atual,
                    max_passos=config.max_passos,
                )

                # 1. RACIOCÍNIO — chama o LLM
                try:
                    mensagens_format = [m.to_llm_format() for m in state.mensagens]
                    resposta_llm = self.llm_client.chat(
                        messages=mensagens_format,
                        model=config.modelo,
                        temperature=config.temperatura,
                    )
                except LLMError as e:
                    logger.error("erro_ao_chamar_llm", erro=str(e))
                    state.status = AgentStatus.ERRO
                    state.erro = f"Erro ao chamar LLM: {e}"
                    return state

                # Adiciona a resposta do LLM ao histórico
                state.adicionar_mensagem("assistant", resposta_llm)

                # 2. DECISÃO — parseia a resposta
                try:
                    resposta = parse_response(resposta_llm)
                except LLMParseError as e:
                    logger.warning(
                        "resposta_llm_invalida",
                        passo=state.passo_atual,
                        erro=str(e),
                    )
                    # Tenta continuar com uma mensagem de erro pro LLM
                    state.adicionar_mensagem(
                        "user",
                        f"Sua resposta não está no formato JSON correto. Erro: {e}. "
                        f"Tente novamente seguindo o formato especificado.",
                    )
                    continue

                # 3a. Se quer usar ferramenta → EXECUÇÃO
                if resposta.is_tool_call:
                    tool_call = resposta.tool_call
                    logger.info(
                        "tool_call_recebido",
                        ferramenta=tool_call.nome,
                        parametros=tool_call.parametros,
                    )

                    # Verifica se a ferramenta existe
                    if not self.registry.has(tool_call.nome):
                        logger.warning(
                            "ferramenta_nao_encontrada",
                            ferramenta=tool_call.nome,
                        )
                        state.adicionar_mensagem(
                            "user",
                            f"Erro: Ferramenta '{tool_call.nome}' não existe. "
                            f"Ferramentas disponíveis: {', '.join(self.registry.list_names())}",
                        )
                        continue

                    # Executa a ferramenta com retry
                    resultado_tool = self._executar_com_retry(
                        tool_call.nome, tool_call.parametros
                    )

                    state.registrar_ferramenta(tool_call.nome)

                    # Adiciona o resultado ao histórico
                    resultado_texto = resultado_tool.resultado.to_prompt_text()
                    state.adicionar_mensagem(
                        "tool",
                        resultado_texto,
                        ferramenta=tool_call.nome,
                    )

                # 3b. Se quer finalizar → FINALIZAÇÃO
                elif resposta.is_final:
                    state.resultado = resposta.final_text
                    state.status = AgentStatus.FINALIZADO
                    logger.info(
                        "agente_finalizado",
                        passo=state.passo_atual,
                        tamanho_resposta=len(resposta.final_text or ""),
                    )
                    break

            else:
                # Loop terminou por max_passos
                logger.warning(
                    "limite_passos_atingido",
                    max_passos=config.max_passos,
                )
                state.status = AgentStatus.TIMEOUT
                state.erro = f"Limite de {config.max_passos} passos atingido sem conclusão."

        except Exception as e:
            logger.error(
                "erro_inesperado_executor",
                erro=str(e),
                tipo=type(e).__name__,
            )
            state.status = AgentStatus.ERRO
            state.erro = f"Erro inesperado: {type(e).__name__}: {e}"

        duracao_total = time.perf_counter() - inicio
        state.metadata["duracao_total_s"] = round(duracao_total, 2)

        logger.info(
            "execucao_concluida",
            status=state.status.value,
            duracao_total_s=round(duracao_total, 2),
            passos=state.passo_atual,
        )

        return state

    def _executar_com_retry(
        self, nome: str, parametros: dict[str, Any]
    ) -> Any:
        """Executa uma ferramenta com retry em caso de erro recuperável.

        Args:
            nome: Nome da ferramenta.
            parametros: Parâmetros para a ferramenta.

        Returns:
            ToolExecutionResult.
        """
        last_result = None
        for tentativa in range(self.max_retries + 1):
            result = self.registry.execute(nome, parametros)
            last_result = result

            # Se sucesso ou erro não-recuperável, retorna
            if result.resultado.sucesso or not isinstance(
                result.resultado.erro, str
            ):
                return result

            # Verifica se foi um ToolExecutionError com retry=True
            # (o registry já captura e converte pra ToolResult.falha)
            if tentativa < self.max_retries:
                logger.info(
                    "retry_ferramenta",
                    ferramenta=nome,
                    tentativa=tentativa + 1,
                    max_retries=self.max_retries,
                )
                time.sleep(2 ** tentativa)  # Backoff exponencial: 1s, 2s, 4s...

        return last_result