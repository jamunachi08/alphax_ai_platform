import frappe


def log_audit(user: str, agent_key: str, provider_meta: dict, trace: dict):
    try:
        frappe.get_doc({
            "doctype": "AI Audit Log",
            "user": user,
            "agent_key": agent_key,
            "provider": provider_meta.get("key"),
            "model": (provider_meta.get("usage") or {}).get("model"),
            "usage_json": frappe.as_json(provider_meta.get("usage")),
            "trace_json": frappe.as_json(trace),
        }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "AlphaX AI Audit Log Failed")
