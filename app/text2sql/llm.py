"""Provider interface and first text-to-SQL provider implementation."""
from __future__ import annotations

from typing import Protocol

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER


class LLMError(RuntimeError):
    """Raised when the configured LLM cannot generate SQL."""


class LLMProvider(Protocol):
    def generate_sql(self, question: str, schema_prompt: str, error: str | None = None) -> str:
        ...


class GroqProvider:
    """Groq chat-completions provider using the existing groq dependency."""

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        from groq import Groq

        client_args = {"api_key": api_key}
        if base_url:
            client_args["base_url"] = base_url
        self._client = Groq(**client_args)
        self._model = model

    def generate_sql(self, question: str, schema_prompt: str, error: str | None = None) -> str:
        retry_context = f"\nThe previous SQL failed with this database error: {error}\n" if error else ""
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            messages=[
                {"role": "system", "content": schema_prompt},
                {"role": "user", "content": f"Question: {question}{retry_context}\nReturn SQL only."},
            ],
        )
        content = response.choices[0].message.content
        if not content:
            raise LLMError("The LLM returned an empty response.")
        return content.strip()


def get_llm_provider() -> LLMProvider:
    """Construct the configured provider without exposing credentials."""
    if not LLM_API_KEY:
        raise LLMError("LLM_API_KEY is not configured.")
    if LLM_PROVIDER.lower() == "groq":
        return GroqProvider(LLM_API_KEY, LLM_MODEL, LLM_BASE_URL)
    raise LLMError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")