from typing import Dict, List, Optional
from .base import BaseProvider, ProviderResponse


class MockProvider(BaseProvider):
    key = "mock"
    label = "Mock Provider"

    def chat(self, messages: List[Dict[str, str]], *, model: Optional[str] = None, temperature: float = 0.2, **kwargs) -> ProviderResponse:
        last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        content = f"[Mock AI] I received: {last_user}"
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost": 0}
        return ProviderResponse(content=content, usage=usage, raw=None)
