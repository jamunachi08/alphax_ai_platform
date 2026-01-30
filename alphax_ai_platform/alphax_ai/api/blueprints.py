from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import frappe
from frappe import _


def _meta_fields(target_doctype: str) -> List[Dict[str, Any]]:
    meta = frappe.get_meta(target_doctype)
    out = []
    for df in meta.fields:
        if df.fieldtype in ("Section Break", "Column Break", "Tab Break", "HTML", "Button", "Fold", "Heading"):
            continue
        if not df.fieldname:
            continue
        out.append({
            "fieldname": df.fieldname,
            "label": df.label,
            "fieldtype": df.fieldtype,
            "options": df.options,
            "reqd": int(getattr(df, "reqd", 0) or 0),
        })
    return out


@frappe.whitelist()
def get_doctype_fields(target_doctype: str) -> Dict[str, Any]:
    if not target_doctype:
        frappe.throw(_("target_doctype is required"))
    return {"fields": _meta_fields(target_doctype)}


@frappe.whitelist()
def save_blueprint(data: Any) -> Dict[str, Any]:
    """Create or update an AI Intake Blueprint.

    `data` should be a dict with:
      - blueprint_name, target_doctype, default_ocr_engine, allow_user_override, language_hint, extraction_mode
      - schema_fields: list of child rows (field_key, label, data_type, required, maps_to, table_child, table_row_field, etc.)
    """
    if isinstance(data, str):
        data = json.loads(data)

    blueprint_name = (data.get("blueprint_name") or "").strip()
    target_doctype = (data.get("target_doctype") or "").strip()
    if not blueprint_name or not target_doctype:
        frappe.throw(_("blueprint_name and target_doctype are required"))

    name = blueprint_name  # autoname uses field:blueprint_name
    exists = frappe.db.exists("AI Intake Blueprint", name)

    doc_dict = {
        "doctype": "AI Intake Blueprint",
        "blueprint_name": blueprint_name,
        "target_doctype": target_doctype,
        "is_template": int(data.get("is_template") or 0),
        "input_types": data.get("input_types") or "PDF\nImage\nExcel",
        "default_ocr_engine": data.get("default_ocr_engine") or "On-Prem",
        "allow_user_override": int(data.get("allow_user_override") or 0),
        "language_hint": data.get("language_hint") or "auto",
        "extraction_mode": data.get("extraction_mode") or "Schema-first",
        "mapping_template": data.get("mapping_template"),
        "notes": data.get("notes") or "",
    }

    if exists:
        doc = frappe.get_doc("AI Intake Blueprint", name)
        doc.update(doc_dict)
        doc.set("schema_fields", [])
    else:
        doc = frappe.get_doc(doc_dict)

    for row in (data.get("schema_fields") or []):
        doc.append("schema_fields", {
            "field_key": row.get("field_key") or "",
            "label": row.get("label") or "",
            "data_type": row.get("data_type") or "String",
            "required": int(row.get("required") or 0),
            "confidence_threshold": float(row.get("confidence_threshold") or 0.6),
            "example_value": row.get("example_value") or "",
            "normalize_rule": row.get("normalize_rule") or "None",
            "maps_to": row.get("maps_to") or "",
            "table_child": row.get("table_child") or "",
            "table_row_field": row.get("table_row_field") or "",
            "notes": row.get("notes") or "",
        })

    if exists:
        doc.save(ignore_permissions=False)
    else:
        doc.insert(ignore_permissions=False)

    return {"ok": True, "name": doc.name}


@frappe.whitelist()
def list_templates() -> Dict[str, Any]:
    rows = frappe.get_all("AI Intake Blueprint", filters={"is_template": 1}, fields=["name", "blueprint_name", "target_doctype"], order_by="modified desc")
    return {"templates": rows}


@frappe.whitelist()
def get_blueprint(name: str) -> Dict[str, Any]:
    doc = frappe.get_doc("AI Intake Blueprint", name)
    payload = doc.as_dict()
    payload["_doctype_fields"] = _meta_fields(doc.target_doctype)
    return payload


@frappe.whitelist()
def test_ingest(file_url: str, blueprint_name: str) -> Dict[str, Any]:
    if not file_url:
        frappe.throw(_("file_url is required"))
    if not blueprint_name:
        frappe.throw(_("blueprint_name is required"))

    from alphax_ai_platform.alphax_ai.api.ingest import ingest_file
    return ingest_file(file_url=file_url, blueprint_name=blueprint_name, create_draft=1)
