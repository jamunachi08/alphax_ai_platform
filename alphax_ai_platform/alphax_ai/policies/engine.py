from .redaction import apply_redaction


class PolicyEngine:
    @staticmethod
    def for_user(user: str, company: str = None):
        return PolicyEngine()

    def evaluate(self, context: dict):
        # MVP policy: read-only; budget placeholders; redaction enabled.
        policy = {
            "model": None,
            "temperature": 0.2,
            "allow_write_tools": False,
            "redaction": True,
            "budget": {"hard_stop": False, "remaining": None},
        }
        if policy.get("redaction"):
            context = apply_redaction(context)
        policy["context"] = context
        return policy
