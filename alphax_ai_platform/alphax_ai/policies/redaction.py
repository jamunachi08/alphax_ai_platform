import re

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)


def apply_redaction(context: dict):
    def scrub(v):
        if isinstance(v, str):
            return EMAIL_RE.sub("[REDACTED_EMAIL]", v)
        if isinstance(v, dict):
            return {k: scrub(val) for k, val in v.items()}
        if isinstance(v, list):
            return [scrub(x) for x in v]
        return v

    return scrub(context)
