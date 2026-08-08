"""Estado do agente durante execução.

O AgentState é o objeto que circula pelo loop de execução.
Cada passo do loop lê, modifica e devolve o estado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    """Status da execução do agente."""

    PENDENTE = "pendente"
    EM_EXECUCAO = "em_execucao"
    FINALIZADO = "finalizado"
    ERRO = "erro"
    TIMEOUT = "timeout"


@dataclass
class Message:
    """Uma mensagem no histórico da conversa com o LLM.

    Attributes:
        role: Papel da mensagem (system, user, assistant, tool).
        content: Conteúdo textual da mensagem.
        metadata: Metadados extras (ex: qual ferramenta foi chamada).
    """

    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_llm_format(self) -> dict[str, str]:
        """Converte para o formato esperado pela API do LLM."""
        return {"role": self.role, "content": self.content}


@dataclass
class AgentState:
    """Estado completo da execução de um agente.

    Attributes:
        mensagens: Histórico da conversa com o LLM.
        passo_atual: Contador de iterações do loop.
        resultado: Saída final do agente (quando finalizado).
        erro: Mensagem de erro (quando status é ERRO).
        status: Status atual da execução.
        ferramentas_usadas: Lista de ferramentas chamadas (pra logging).
        metadata: Dados extras livres.
    """

    mensagens: list[Message] = field(default_factory=list)
    passo_atual: int = 0
    resultado: str | None = None
    erro: str | None = None
    status: AgentStatus = AgentStatus.PENDENTE
    ferramentas_usadas: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def adicionar_mensagem(self, role: str, content: str, **metadata: Any) -> None:
        """Adiciona uma mensagem ao histórico."""
        self.mensagens.append(Message(role=role, content=content, metadata=metadata))

    def registrar_ferramenta(self, nome: str) -> None:
        """Registra que uma ferramenta foi usada."""
        self.ferramentas_usadas.append(nome)

    @property
    def finalizado(self) -> bool:
        """True se a execução terminou (com sucesso ou erro)."""
        return self.status in (
            AgentStatus.FINALIZADO,
            AgentStatus.ERRO,
            AgentStatus.TIMEOUT,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serializa o estado (útil pra logging e debug)."""
        return {
            "passo_atual": self.passo_atual,
            "status": self.status.value,
            "resultado": self.resultado,
            "erro": self.erro,
            "num_mensagens": len(self.mensagens),
            "ferramentas_usadas": self.ferramentas_usadas,
        }