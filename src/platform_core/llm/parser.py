"""Parser de resposta do LLM.

Interpreta a resposta do LLM, extraindo a decisão (usar ferramenta
ou finalizar) e seus parâmetros.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from platform_core.logging.structured import get_logger

logger = get_logger(__name__)


@dataclass
class ToolCall:
    """Representa uma chamada de ferramenta solicitada pelo LLM."""

    nome: str
    parametros: dict[str, Any]


@dataclass
class LLMResponse:
    """Resposta parseada do LLM.

    Apenas uma das ações está presente:
    - tool_call: quando o LLM quer usar uma ferramenta
    - final_text: quando o LLM quer finalizar
    """

    tool_call: ToolCall | None = None
    final_text: str | None = None

    @property
    def is_tool_call(self) -> bool:
        return self.tool_call is not None

    @property
    def is_final(self) -> bool:
        return self.final_text is not None


class LLMParseError(Exception):
    """Erro ao interpretar a resposta do LLM."""

    pass


def _extrair_json(raw: str) -> str:
    """Extrai JSON de uma string que pode conter markdown code blocks."""
    texto = raw.strip()

    # Remove code blocks de markdown (```json ... ``` ou ``` ... ```)
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", texto, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Se não tem code block, tenta achar o primeiro { e último }
    start = texto.find("{")
    end = texto.rfind("}")
    if start != -1 and end != -1 and end > start:
        return texto[start : end + 1]

    return texto


def parse_response(raw: str) -> LLMResponse:
    """Interpreta a resposta do LLM.

    Espera um JSON com um dos formatos:
    - {"acao": "usar_ferramenta", "ferramenta": "nome", "parametros": {...}}
    - {"acao": "finalizar", "resposta": "texto final"}

    Args:
        raw: Resposta bruta do LLM.

    Returns:
        LLMResponse parseada.

    Raises:
        LLMParseError: Se a resposta não puder ser interpretada.
    """
    logger.debug("parse_resposta_llm", raw_preview=raw[:200])

    json_text = _extrair_json(raw)
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        logger.warning("json_invalido", erro=str(e), raw=raw[:500])
        raise LLMParseError(
            f"Resposta do LLM não é JSON válido: {e}. Resposta: {raw[:200]}"
        ) from e

    if not isinstance(data, dict):
        raise LLMParseError(
            f"Esperado dict no topo do JSON, recebido: {type(data).__name__}"
        )

    acao = data.get("acao")

    if acao == "usar_ferramenta":
        ferramenta = data.get("ferramenta")
        if not ferramenta or not isinstance(ferramenta, str):
            raise LLMParseError(
                "Campo 'ferramenta' ausente ou inválido para ação 'usar_ferramenta'"
            )
        parametros = data.get("parametros") or {}
        if not isinstance(parametros, dict):
            raise LLMParseError(
                f"Campo 'parametros' deve ser dict, recebido: {type(parametros).__name__}"
            )
        logger.info(
            "resposta_tool_call",
            ferramenta=ferramenta,
            parametros=parametros,
        )
        return LLMResponse(
            tool_call=ToolCall(nome=ferramenta, parametros=parametros)
        )

    if acao == "finalizar":
        resposta = data.get("resposta")
        if resposta is None:
            raise LLMParseError(
                "Campo 'resposta' ausente para ação 'finalizar'"
            )
        if not isinstance(resposta, str):
            resposta = str(resposta)
        logger.info("resposta_final", tamanho=len(resposta))
        return LLMResponse(final_text=resposta)

    raise LLMParseError(
        f"Ação desconhecida: '{acao}'. Esperado 'usar_ferramenta' ou 'finalizar'."
    )