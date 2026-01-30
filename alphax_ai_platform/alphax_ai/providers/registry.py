import frappe
from .mock_provider import MockProvider
from .openai_provider import OpenAIProvider


class ProviderRegistry:
    @staticmethod
    def get_default_provider():
        # Read from AI Platform Settings if available; fallback to mock
        try:
            provider_key = frappe.db.get_single_value("AI Platform Settings", "default_provider")
        except Exception:
            provider_key = None

        if provider_key == "openai":
            return OpenAIProvider()

        return MockProvider()
