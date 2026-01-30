from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ProviderResponse:
    content: str
    usage: Dict[str, Any] | None = None
    raw: Any | None = None


class BaseProvider:
    key: str = "base"
    label: str = "Base Provider"

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.2,
        **kwargs,
    ) -> ProviderResponse:
        raise NotImplementedError
