"""Interface abstrata para clientes de LLM."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMClient(ABC):
    """Interface base para clientes de LLM.

    Todos os provedores (Ollama, OpenAI, etc.) devem implementar
    esta interface para serem usados pelo executor.
    """

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
        """Envia mensagens ao LLM e retorna a resposta textual.

        Args:
            messages: Lista de mensagens no formato {"role": "...", "content": "..."}.
            model: Identificador do modelo a usar.
            temperature: Temperatura de amostragem (0.0 a 2.0).
            **kwargs: Parâmetros adicionais específicos do provedor.

        Returns:
            Resposta textual do LLM.

        Raises:
            LLMError: Se houver erro na comunicação com o LLM.
        """
        pass


class LLMError(Exception):
    """Erro genérico de comunicação com LLM."""

    pass
