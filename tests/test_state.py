"""Testes do AgentState."""

from platform_core.engine.state import AgentState, AgentStatus, Message


class TestMessage:
    def test_to_llm_format(self):
        msg = Message(role="user", content="olá")
        formato = msg.to_llm_format()
        assert formato == {"role": "user", "content": "olá"}


class TestAgentState:
    def test_estado_inicial(self):
        state = AgentState()
        assert state.passo_atual == 0
        assert state.status == AgentStatus.PENDENTE
        assert state.mensagens == []
        assert state.finalizado is False

    def test_adicionar_mensagem(self):
        state = AgentState()
        state.adicionar_mensagem("user", "teste")
        assert len(state.mensagens) == 1
        assert state.mensagens[0].role == "user"
        assert state.mensagens[0].content == "teste"

    def test_registrar_ferramenta(self):
        state = AgentState()
        state.registrar_ferramenta("google_calendar_list_events")
        assert "google_calendar_list_events" in state.ferramentas_usadas

    def test_finalizado_com_sucesso(self):
        state = AgentState()
        state.status = AgentStatus.FINALIZADO
        assert state.finalizado is True

    def test_finalizado_com_erro(self):
        state = AgentState()
        state.status = AgentStatus.ERRO
        assert state.finalizado is True

    def test_to_dict(self):
        state = AgentState()
        state.status = AgentStatus.EM_EXECUCAO
        d = state.to_dict()
        assert d["status"] == "em_execucao"
        assert d["passo_atual"] == 0
