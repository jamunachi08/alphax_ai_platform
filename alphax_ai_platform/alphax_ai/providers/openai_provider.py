import os
from typing import Dict, List, Optional
from .base import BaseProvider, ProviderResponse


class OpenAIProvider(BaseProvider):
    key = "openai"
    label = "OpenAI"

    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")

    def chat(self, messages: List[Dict[str, str]], *, model: Optional[str] = None, temperature: float = 0.2, **kwargs) -> ProviderResponse:
        # Skeleton stub:
        # - works even if OpenAI SDK is not installed
        # - replace with real SDK integration in Phase-1 hardening
        if not self.api_key:
            return ProviderResponse(
                content="OpenAI provider is not configured. Set OPENAI_API_KEY and select OpenAI as default provider in AI Platform Settings.",
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost": 0},
                raw=None,
            )

        return ProviderResponse(
            content="OpenAI provider stub is installed. Wire the official SDK/HTTP client in alphax_ai/providers/openai_provider.py.",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost": 0},
            raw=None,
        )
