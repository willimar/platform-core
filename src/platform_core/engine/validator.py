"""Validação pré-execução de agentes.

Verifica se o agente está "pronto pra decolar":
- Todas as ferramentas declaradas existem no registry
- O modelo está disponível no Ollama (ou outro LLM)
- O timeout é razoável
"""

from __future__ import annotations

import httpx

from platform_core.config.schema import AgentConfig
from platform_core.config.settings import get_settings
from platform_core.logging.structured import get_logger
from platform_core.tools.registry import ToolRegistry

logger = get_logger(__name__)


class ValidationError(Exception):
    """Erro de validação pré-execução."""

    pass


def validar_agente(config: AgentConfig, registry: ToolRegistry) -> None:
    """Valida um agente antes da execução.

    Args:
        config: Configuração do agente.
        registry: Registry com as ferramentas carregadas.

    Raises:
        ValidationError: Se alguma validação falhar.
    """
    logger.info(
        "validando_agente",
        nome=config.nome,
        modelo=config.modelo,
        ferramentas=config.ferramentas,
    )

    # 1. Ferramentas declaradas existem?
    faltando = [t for t in config.ferramentas if not registry.has(t)]
    if faltando:
        msg = (
            f"Ferramentas declaradas no YAML não encontradas no registry: "
            f"{', '.join(faltando)}"
        )
        logger.error("ferramentas_faltando", faltando=faltando)
        raise ValidationError(msg)

    # 2. Modelo disponível no Ollama?
    if config.modelo == "fake":
        logger.info("modelo_fake_detectado", modelo=config.modelo)
    else:
        _verificar_modelo_ollama(config.modelo)

    # 3. Timeout razoável
    if config.timeout_segundos < 10:
        logger.warning(
            "timeout_muito_baixo",
            timeout=config.timeout_segundos,
        )

    logger.info("agente_validado", nome=config.nome)


def _verificar_modelo_ollama(modelo: str) -> None:
    """Verifica se o modelo está disponível no Ollama.

    Args:
        modelo: Nome do modelo (ex: "llama3.1:8b").

    Raises:
        ValidationError: Se o modelo não estiver disponível.
    """
    settings = get_settings()
    url = f"{settings.ollama_base_url}/api/tags"

    try:
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
    except Exception as e:
        logger.warning(
            "ollama_indisponivel",
            url=url,
            erro=str(e),
            tipo=type(e).__name__,
        )
        # Não falha a validação — Ollama pode estar offline agora
        # mas funcionar quando o executor chamar
        return

    try:
        data = response.json()
    except Exception as e:
        logger.warning("resposta_ollama_invalida", erro=str(e))
        return

    modelos = data.get("models", [])
    nomes = [m.get("name", "") for m in modelos]

    # Ollama aceita "llama3.1:8b" ou "llama3.1:8b-instruct-q4_0"
    # Verifica se o modelo pedido está na lista (match exato ou prefixo)
    modelo_encontrado = any(
        nome == modelo or nome.startswith(modelo) for nome in nomes
    )

    if not modelo_encontrado:
        msg = (
            f"Modelo '{modelo}' não encontrado no Ollama. "
            f"Modelos disponíveis: {', '.join(nomes) if nomes else '(nenhum)'}"
        )
        logger.error("modelo_nao_encontrado", modelo=modelo, disponiveis=nomes)
        raise ValidationError(msg)

    logger.info("modelo_disponivel", modelo=modelo)