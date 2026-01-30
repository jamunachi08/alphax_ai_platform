from __future__ import annotations
from typing import Any, Dict


class AgentEngine:
    def __init__(self, agent_key: str, system_prompt: str, policy: Dict[str, Any], context: Dict[str, Any]):
        self.agent_key = agent_key
        self.system_prompt = system_prompt
        self.policy = policy or {}
        self.context = context or {}

    def run(self, provider, user_message: str):
        # MVP: single-turn assistant (Phase-2 adds multi-step tool calls)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        resp = provider.chat(messages, model=self.policy.get("model"), temperature=self.policy.get("temperature", 0.2))

        trace = {
            "provider": {
                "key": getattr(provider, "key", "unknown"),
                "label": getattr(provider, "label", "unknown"),
                "usage": resp.usage or {},
            },
            "tools": [],
            "policy": {k: v for k, v in (self.policy or {}).items() if k != "context"},
        }
        return resp.content, trace
