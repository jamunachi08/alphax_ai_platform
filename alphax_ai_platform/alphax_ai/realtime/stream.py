import frappe


def publish(session_id: str, payload: dict):
    frappe.publish_realtime(
        event=f"alphax_ai_stream::{session_id}",
        message=payload,
        user=frappe.session.user,
    )
