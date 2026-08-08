"""Testes do parser de resposta do LLM."""

import pytest

from platform_core.llm.parser import LLMParseError, parse_response


class TestParser:
    def test_tool_call_simples(self):
        raw = '{"acao": "usar_ferramenta", "ferramenta": "test_tool", "parametros": {"qtd": 5}}'
        resp = parse_response(raw)
        assert resp.is_tool_call
        assert resp.tool_call.nome == "test_tool"
        assert resp.tool_call.parametros == {"qtd": 5}

    def test_finalizar_simples(self):
        raw = '{"acao": "finalizar", "resposta": "Pronto!"}'
        resp = parse_response(raw)
        assert resp.is_final
        assert resp.final_text == "Pronto!"

    def test_extrai_de_code_block_markdown(self):
        raw = '```json\n{"acao": "finalizar", "resposta": "ok"}\n```'
        resp = parse_response(raw)
        assert resp.is_final

    def test_extrai_json_no_meio_de_texto(self):
        raw = 'Pensando...\n{"acao": "finalizar", "resposta": "ok"}\nFim.'
        resp = parse_response(raw)
        assert resp.is_final

    def test_json_invalido(self):
        with pytest.raises(LLMParseError):
            parse_response("isso não é json")

    def test_acao_desconhecida(self):
        with pytest.raises(LLMParseError, match="Ação desconhecida"):
            parse_response('{"acao": "voar"}')

    def test_tool_call_sem_ferramenta(self):
        with pytest.raises(LLMParseError):
            parse_response('{"acao": "usar_ferramenta"}')

    def test_finalizar_sem_resposta(self):
        with pytest.raises(LLMParseError):
            parse_response('{"acao": "finalizar"}')

    def test_parametros_default_vazio(self):
        raw = '{"acao": "usar_ferramenta", "ferramenta": "test"}'
        resp = parse_response(raw)
        assert resp.tool_call.parametros == {}