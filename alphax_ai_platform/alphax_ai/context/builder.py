import frappe


def build_context(user: str, doctype: str = None, docname: str = None):
    ctx = {
        "user": user,
        "roles": frappe.get_roles(user),
        "company": frappe.defaults.get_user_default("Company"),
        "doctype": doctype,
        "docname": docname,
    }

    if doctype and docname:
        try:
            doc = frappe.get_doc(doctype, docname)
            ctx["doc"] = {
                "doctype": doctype,
                "name": docname,
                "title": getattr(doc, "title", None) or getattr(doc, "customer", None) or docname,
            }
        except Exception:
            ctx["doc"] = None

    return ctx
