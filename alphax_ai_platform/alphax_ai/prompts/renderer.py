DEFAULT_SYSTEM_PROMPT = (
    "You are AlphaX AI, an enterprise assistant inside ERPNext. "
    "Be precise, permission-aware, and do not invent ERP data. "
    "Use tools only when allowed."
)


def render_agent_system_prompt(agent_key: str, context: dict, policy: dict):
    parts = [DEFAULT_SYSTEM_PROMPT]
    if context:
        parts.append(
            f"Context: user={context.get('user')}, company={context.get('company')}, "
            f"doctype={context.get('doctype')}, docname={context.get('docname')}"
        )
    return "\n".join(parts)
