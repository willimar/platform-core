"""Carregador de agent.yaml.

Lê o arquivo, valida contra o schema Pydantic e retorna um AgentConfig.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from platform_core.config.schema import AgentConfig
from platform_core.logging.structured import get_logger

logger = get_logger(__name__)


class AgentLoadError(Exception):
    """Erro ao carregar um agent.yaml."""

    pass


def load_agent(path: str | Path) -> AgentConfig:
    """Carrega e valida um agent.yaml.

    Args:
        path: Caminho para o arquivo agent.yaml.

    Returns:
        AgentConfig validado.

    Raises:
        AgentLoadError: Se o arquivo não existir, não for YAML válido
                        ou não seguir o schema.
    """
    caminho = Path(path).resolve()
    logger.info("carregando_agente", caminho=str(caminho))

    if not caminho.exists():
        raise AgentLoadError(f"Arquivo não encontrado: {caminho}")
    if not caminho.is_file():
        raise AgentLoadError(f"Caminho não é um arquivo: {caminho}")

    try:
        with open(caminho, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise AgentLoadError(f"YAML inválido em {caminho}: {e}") from e

    if not isinstance(data, dict):
        raise AgentLoadError(
            f"Esperado dicionário no topo do YAML, recebido: {type(data).__name__}"
        )

    try:
        config = AgentConfig.model_validate(data)
    except Exception as e:
        raise AgentLoadError(f"agent.yaml inválido em {caminho}: {e}") from e

    logger.info(
        "agente_carregado",
        nome=config.nome,
        versao=config.versao,
        modelo=config.modelo,
        ferramentas=config.ferramentas,
    )
    return config


def resolve_tools_dir(agent_path: Path, config: AgentConfig) -> Path:
    """Resolve o diretório de ferramentas do agente.

    Ordem de precedência:
    1. Campo tools_dir no YAML (relativo ao diretório-pai do YAML)
    2. Convenção: tools/ ao lado do YAML
    3. Busca ascendente limitada (até 3 níveis) por tools/

    Args:
        agent_path: Caminho do YAML do agente.
        config: Configuração carregada do agente.

    Returns:
        Path resolvido do diretório de ferramentas (pode não existir;
        o CLI emite o aviso de sempre nesse caso).
    """
    base = agent_path.resolve().parent

    # 1. Explícito vence
    if config.tools_dir:
        return (base / config.tools_dir).resolve()

    # 2. Convenção
    convencional = base / "tools"
    if convencional.exists():
        return convencional

    # 3. Fallback ascendente limitado
    for ancestor in [base, *base.parents[:3]]:
        candidato = ancestor / "tools"
        if candidato.exists():
            logger.info(
                "tools_dir_resolvido_por_busca",
                yaml=str(agent_path),
                tools_dir=str(candidato),
            )
            return candidato

    return convencional
