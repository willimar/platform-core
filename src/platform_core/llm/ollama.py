"""Cliente HTTP para Ollama."""

from __future__ import annotations

import os
from typing import Any

import httpx

from platform_core.llm.client import LLMClient, LLMError
from platform_core.logging.structured import get_logger

logger = get_logger(__name__)


class OllamaClient(LLMClient):
    """Cliente para Ollama via API HTTP.

    Usa o endpoint /api/chat compatível com o formato OpenAI.

    Args:
        base_url: URL base do Ollama (default: http://localhost:11434).
        timeout: Timeout em segundos (default: 120).
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ).rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
        """Envia mensagens ao Ollama e retorna a resposta.

        Args:
            messages: Lista de mensagens no formato {"role": "...", "content": "..."}.
            model: Nome do modelo (ex: "llama3.1:8b").
            temperature: Temperatura de amostragem.

        Returns:
            Resposta textual do LLM.

        Raises:
            LLMError: Se houver erro na comunicação ou resposta inválida.
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        logger.info(
            "chamando_ollama",
            model=model,
            num_mensagens=len(messages),
            temperature=temperature,
        )

        try:
            response = self._client.post(url, json=payload)
            response.raise_for_status()
        except httpx.TimeoutException as e:
            logger.error("ollama_timeout", timeout=self.timeout)
            raise LLMError(f"Timeout ao chamar Ollama após {self.timeout}s") from e
        except httpx.ConnectError as e:
            logger.error("ollama_conexao_falhou", url=url)
            raise LLMError(
                f"Não foi possível conectar ao Ollama em {self.base_url}. "
                f"Verifique se o Ollama está rodando."
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error(
                "ollama_erro_http",
                status_code=e.response.status_code,
                response=e.response.text[:500],
            )
            raise LLMError(
                f"Ollama retornou erro HTTP {e.response.status_code}: "
                f"{e.response.text[:200]}"
            ) from e

        try:
            data = response.json()
        except Exception as e:
            logger.error("ollama_resposta_nao_json", raw=response.text[:500])
            raise LLMError(f"Resposta do Ollama não é JSON válido: {e}") from e

        if "message" not in data or "content" not in data["message"]:
            logger.error("ollama_resposta_invalida", data=data)
            raise LLMError(
                f"Resposta do Ollama não contém 'message.content': {data}"
            )

        content = data["message"]["content"]
        logger.info(
            "ollama_resposta_recebida",
            tamanho=len(content),
            preview=content[:100],
        )
        return content

    def close(self) -> None:
        """Fecha a conexão HTTP."""
        self._client.close()

    def __enter__(self) -> OllamaClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()