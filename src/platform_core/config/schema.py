"""Schemas Pydantic para agent.yaml.

Define o contrato tipado que um arquivo agent.yaml deve seguir.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


class TarefaSpec(BaseModel):
    """Especificação da tarefa do agente."""

    descricao: str = Field(..., min_length=5, description="O que o agente deve fazer")
    saida_esperada: str = Field(
        ...,
        min_length=5,
        description="Critério de sucesso / formato da resposta",
    )


class AgentConfig(BaseModel):
    """Configuração completa de um agente, carregada do agent.yaml.

    Este é o objeto central que a engine recebe após validação.
    """

    nome: str = Field(..., min_length=1, description="Nome legível do agente")
    versao: str = Field(..., description="Versão semântica (MAJOR.MINOR.PATCH)")
    modelo: str = Field(..., description="Identificador do LLM")
    instrucoes: str = Field(..., min_length=10, description="System prompt do agente")
    ferramentas: list[str] = Field(
        ..., min_length=1, description="Nomes das ferramentas disponíveis"
    )
    tarefa: TarefaSpec = Field(..., description="Especificação da tarefa")

    # Opcionais
    temperatura: float = Field(default=0.1, ge=0.0, le=2.0)
    max_passos: int = Field(default=5, ge=1, le=50)
    timeout_segundos: int = Field(default=120, ge=10, le=3600)
    modelo_fallback: str | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("versao")
    @classmethod
    def validar_semver(cls, v: str) -> str:
        """Valida que a versão segue SemVer."""
        if not SEMVER_PATTERN.match(v):
            raise ValueError(f"Versão '{v}' não segue o formato SemVer (MAJOR.MINOR.PATCH)")
        return v

    @field_validator("ferramentas")
    @classmethod
    def validar_ferramentas(cls, v: list[str]) -> list[str]:
        """Valida que os nomes de ferramentas estão bem formados."""
        for nome in v:
            if not nome or not nome.strip():
                raise ValueError("Nome de ferramenta não pode ser vazio")
            if " " in nome:
                raise ValueError(f"Nome de ferramenta não pode conter espaços: '{nome}'")
        # Remove duplicatas preservando ordem
        seen: set[str] = set()
        sem_dup: list[str] = []
        for nome in v:
            if nome not in seen:
                seen.add(nome)
                sem_dup.append(nome)
        return sem_dup
