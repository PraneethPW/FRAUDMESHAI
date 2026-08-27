from abc import ABC, abstractmethod

import httpx

from app.core.config import settings


SYSTEM_PROMPT = "You are an investigation writing assistant. Use only the structured evidence supplied. Never invent facts, transactions, entities, scores, or conclusions. State uncertainty and leave fraud decisions to the analyst."


class AIProvider(ABC):
    name = "unavailable"

    @abstractmethod
    async def summarize(self, evidence: dict, question: str | None = None) -> str: ...


class OpenAICompatibleProvider(AIProvider):
    def __init__(self, name: str, base_url: str, api_key: str, model: str) -> None:
        self.name, self.base_url, self.api_key, self.model = name, base_url, api_key, model

    async def summarize(self, evidence: dict, question: str | None = None) -> str:
        prompt = f"Structured verified evidence:\n{evidence}\n\nTask: {question or 'Write a concise investigator briefing.'}"
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", **({"HTTP-Referer": settings.frontend_url, "X-Title": settings.app_name} if self.name == "openrouter" else {})}, json={"model": self.model, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}], "temperature": 0.1})
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]


def get_provider() -> AIProvider | None:
    if settings.openrouter_api_key and settings.openrouter_model:
        return OpenAICompatibleProvider("openrouter", "https://openrouter.ai/api/v1", settings.openrouter_api_key, settings.openrouter_model)
    if settings.openai_api_key and settings.openai_model:
        return OpenAICompatibleProvider("openai", "https://api.openai.com/v1", settings.openai_api_key, settings.openai_model)
    return None

