"""Testes do executor com LLM fake (sem rede, sem Ollama)."""

from __future__ import annotations

from agent_sdk import ToolExecutionError
from agent_sdk.types import ToolSpec
from platform_core.config.schema import AgentConfig, TarefaSpec
from platform_core.engine.executor import Executor
from platform_core.engine.state import AgentStatus
from platform_core.llm.client import LLMClient
from platform_core.tools.registry import ToolRegistry


class FakeLLM(LLMClient):
    """LLM de teste que devolve respostas roteirizadas."""

    def __init__(self, respostas: list[str]):
        self.respostas = list(respostas)
        self.chamadas = 0

    def chat(self, messages, model, temperature=0.1, **kwargs):
        self.chamadas += 1
        if self.respostas:
            return self.respostas.pop(0)
        return '{"acao": "finalizar", "resposta": "fim"}'


# ── Ferramentas fake ───────────────────────────────────────────
# Definidas como funções simples + ToolSpec explícito.
# NÃO usamos @tool aqui para não depender do registry global.


class FakeState:
    """Estado mutável das ferramentas fake (contadores)."""

    def __init__(self):
        self.retry_falhas = 0
        self.noretry_chamadas = 0
        self.ok_chamadas = 0

    def reset(self):
        self.retry_falhas = 0
        self.noretry_chamadas = 0
        self.ok_chamadas = 0


def _fake_ok(state: FakeState, x: int = 1) -> str:
    state.ok_chamadas += 1
    return f"ok {x}"


def _fake_retry(state: FakeState) -> str:
    if state.retry_falhas < 1:
        state.retry_falhas += 1
        raise ToolExecutionError("falha transitoria", retry=True)
    return "recuperado"


def _fake_fatal(state: FakeState) -> str:
    state.noretry_chamadas += 1
    raise ToolExecutionError("falha fatal", retry=False)


# ── Helpers ────────────────────────────────────────────────────


def _make_specs(state: FakeState) -> list[ToolSpec]:
    """Cria as ToolSpecs das ferramentas fake, fechando sobre o state."""
    return [
        ToolSpec(
            nome="fake_ok",
            descricao="Fake que sempre funciona.",
            descricao_completa="Fake que sempre funciona.",
            parametros={"x": {"tipo": "int", "default": 1}},
            funcao=lambda x=1: _fake_ok(state, x),
        ),
        ToolSpec(
            nome="fake_retry",
            descricao="Fake que falha uma vez (transitorio).",
            descricao_completa="Fake que falha uma vez e depois funciona.",
            parametros={},
            funcao=lambda: _fake_retry(state),
        ),
        ToolSpec(
            nome="fake_fatal",
            descricao="Fake que falha sem retry.",
            descricao_completa="Fake que falha fatalmente.",
            parametros={},
            funcao=lambda: _fake_fatal(state),
        ),
    ]


def make_config(
    ferramentas: list[str],
    timeout_segundos: int = 60,
    **overrides,
) -> AgentConfig:
    """Constrói um AgentConfig válido (min_length=5 nos strings)."""
    base = dict(
        nome="Teste",
        versao="1.0.0",
        modelo="fake",
        instrucoes="Instrucoes de teste com tamanho minimo ok.",
        ferramentas=ferramentas,
        tarefa=TarefaSpec(
            descricao="Faca algo.",
            saida_esperada="Algo feito.",
        ),
        max_passos=5,
        timeout_segundos=timeout_segundos,
        temperatura=0.1,
    )
    base.update(overrides)
    return AgentConfig(**base)


def make_executor(
    respostas: list[str],
    ferramentas: list[str],
) -> tuple[Executor, FakeLLM, FakeState]:
    """Monta um executor com LLM fake e ferramentas fake locais."""
    state = FakeState()
    registry = ToolRegistry()
    specs_por_nome = {s.nome: s for s in _make_specs(state)}
    for nome in ferramentas:
        registry.register(specs_por_nome[nome])

    llm = FakeLLM(respostas)
    return (
        Executor(llm_client=llm, registry=registry, max_retries=2),
        llm,
        state,
    )


TOOL_CALL_OK = '{"acao": "usar_ferramenta", "ferramenta": "fake_ok", "parametros": {"x": 7}}'
TOOL_CALL_RETRY = '{"acao": "usar_ferramenta", "ferramenta": "fake_retry", "parametros": {}}'
TOOL_CALL_FATAL = '{"acao": "usar_ferramenta", "ferramenta": "fake_fatal", "parametros": {}}'
FINAL = '{"acao": "finalizar", "resposta": "terminei"}'


# ── Testes ─────────────────────────────────────────────────────


class TestExecutor:
    def test_finaliza_imediato(self):
        executor, llm, _ = make_executor([FINAL], ["fake_ok"])
        state = executor.executar(make_config(["fake_ok"]))
        assert state.status == AgentStatus.FINALIZADO
        assert state.resultado == "terminei"
        assert state.passo_atual == 1
        assert llm.chamadas == 1

    def test_tool_call_entao_finaliza(self):
        executor, _, st = make_executor([TOOL_CALL_OK, FINAL], ["fake_ok"])
        state = executor.executar(make_config(["fake_ok"]))
        assert state.status == AgentStatus.FINALIZADO
        assert state.ferramentas_usadas == ["fake_ok"]
        assert st.ok_chamadas == 1

    def test_retry_recupera_erro_transitorio(self):
        executor, _, st = make_executor([TOOL_CALL_RETRY, FINAL], ["fake_retry"])
        state = executor.executar(make_config(["fake_retry"]))
        assert state.status == AgentStatus.FINALIZADO
        # 1 falha + 1 sucesso = a ferramenta foi chamada 2 vezes
        assert st.retry_falhas == 1

    def test_erro_fatal_nao_repete(self):
        executor, _, st = make_executor([TOOL_CALL_FATAL, FINAL], ["fake_fatal"])
        state = executor.executar(make_config(["fake_fatal"]))
        assert state.status == AgentStatus.FINALIZADO
        # Sem retry: exatamente 1 chamada, mesmo com max_retries=2
        assert st.noretry_chamadas == 1

    def test_limite_de_passos(self):
        executor, _, _ = make_executor([TOOL_CALL_OK] * 10, ["fake_ok"])
        state = executor.executar(make_config(["fake_ok"], max_passos=2))
        assert state.status == AgentStatus.TIMEOUT
        assert "passos" in state.erro

    def test_timeout_global(self, monkeypatch):
        """Timeout deve disparar antes de executar passos quando tempo excedido.

        Mockamos time.perf_counter para simular passagem de tempo sem delay real.
        """
        config = make_config(["fake_ok"], timeout_segundos=10)
        executor, llm, _ = make_executor([TOOL_CALL_OK, FINAL], ["fake_ok"])

        # Mock do tempo: inicio=0, depois 100s (ultrapassa timeout de 10s)
        tempos = [0, 100, 100, 100]
        monkeypatch.setattr(
            "platform_core.engine.executor.time.perf_counter",
            lambda: tempos.pop(0) if tempos else 100,
        )

        state = executor.executar(config)
        assert state.status == AgentStatus.TIMEOUT
        assert "Timeout" in state.erro
        # Nenhum passo deve ter executado (timeout disparou antes do primeiro passo)
        assert state.passo_atual == 0
        # LLM nunca foi chamado
        assert llm.chamadas == 0

    def test_ferramenta_inexistente_volta_para_llm(self):
        """Se o LLM pede uma ferramenta que não existe, o executor
        informa e o loop continua."""
        call_ruim = '{"acao": "usar_ferramenta", "ferramenta": "nao_existe", "parametros": {}}'
        executor, llm, _ = make_executor([call_ruim, FINAL], ["fake_ok"])
        state = executor.executar(make_config(["fake_ok"]))
        assert state.status == AgentStatus.FINALIZADO
        # Pelo menos 2 chamadas ao LLM: a do erro + a que finalizou
        assert llm.chamadas == 2

    def test_json_invalido_pede_nova_tentativa(self):
        """JSON malformado é sinalizado ao LLM, que tenta de novo."""
        executor, llm, _ = make_executor(["nao eh json", FINAL], ["fake_ok"])
        state = executor.executar(make_config(["fake_ok"]))
        assert state.status == AgentStatus.FINALIZADO
        assert llm.chamadas == 2

    def test_resposta_inclui_mensagem_de_erro_da_tool(self):
        """Quando a tool falha, o LLM recebe o texto de erro no histórico."""
        executor, _, _ = make_executor([TOOL_CALL_FATAL, FINAL], ["fake_fatal"])
        state = executor.executar(make_config(["fake_fatal"]))
        # Procura se o texto de erro foi anexado ao histórico
        tool_msgs = [m for m in state.mensagens if m.role == "tool"]
        assert len(tool_msgs) == 1
        assert "falha fatal" in tool_msgs[0].content
        assert "nao tente novamente" in tool_msgs[0].content
