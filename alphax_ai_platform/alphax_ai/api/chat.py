import frappe
from alphax_ai_platform.alphax_ai.providers.registry import ProviderRegistry
from alphax_ai_platform.alphax_ai.context.builder import build_context
from alphax_ai_platform.alphax_ai.policies.engine import PolicyEngine
from alphax_ai_platform.alphax_ai.logs.audit import log_audit
from alphax_ai_platform.alphax_ai.prompts.renderer import render_agent_system_prompt
from alphax_ai_platform.alphax_ai.agents.engine import AgentEngine


@frappe.whitelist(methods=["POST", "GET"])
def chat(agent_key: str, message: str, session_id: str = None, doctype: str = None, docname: str = None):
    """AlphaX AI chat endpoint (MVP).

    Phase-1: single-turn assistant.
    Phase-2: multi-step tool calling + approvals.
    """
    if not agent_key:
        frappe.throw("agent_key is required")
    if not message:
        frappe.throw("message is required")

    user = frappe.session.user

    # Create / fetch session
    if not session_id:
        session = frappe.get_doc({
            "doctype": "AI Chat Session",
            "user": user,
            "company": frappe.defaults.get_user_default("Company"),
            "context_doctype": doctype or "",
            "context_docname": docname or "",
            "status": "Open",
        }).insert(ignore_permissions=True)
        session_id = session.name
    else:
        session = frappe.get_doc("AI Chat Session", session_id)

    # Persist user message
    frappe.get_doc({
        "doctype": "AI Chat Message",
        "session": session_id,
        "role": "user",
        "content": message,
    }).insert(ignore_permissions=True)

    context = build_context(user=user, doctype=doctype, docname=docname)
    policy = PolicyEngine.for_user(user=user, company=session.company).evaluate(context=context)

    system_prompt = render_agent_system_prompt(agent_key=agent_key, context=context, policy=policy)
    engine = AgentEngine(agent_key=agent_key, system_prompt=system_prompt, policy=policy, context=context)

    provider = ProviderRegistry.get_default_provider()

    reply, trace = engine.run(provider=provider, user_message=message)

    # Persist assistant message
    frappe.get_doc({
        "doctype": "AI Chat Message",
        "session": session_id,
        "role": "assistant",
        "content": reply,
    }).insert(ignore_permissions=True)

    # Audit log (best-effort)
    log_audit(user=user, agent_key=agent_key, provider_meta=trace.get("provider", {}), trace=trace)

    return {"session_id": session_id, "reply": reply, "trace": trace}
