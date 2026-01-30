from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe import _


def apply_schema_field_mapping(parsed: Dict[str, Any], schema_fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Map parsed canonical keys into ERPNext doc dict using schema field config.
    schema_fields rows are AI Extraction Schema Field child rows containing:
      - field_key (source key)
      - maps_to (target field path; supports child like 'items.item_code')
    """
    out: Dict[str, Any] = {}
    items_acc: List[Dict[str, Any]] = []

    for row in (schema_fields or []):
        src = row.get("field_key")
        tgt = row.get("maps_to")
        if not src or not tgt:
            continue

        val = parsed.get(src)
        if val is None or val == "":
            continue

        if "." in tgt:
            parent, child_field = tgt.split(".", 1)
            if parent == "items":
                # if value is list of dicts, merge; else set on all? we only support list-of-dicts keys
                if src == "items" and isinstance(val, list):
                    for v in val:
                        if isinstance(v, dict):
                            items_acc.append(v)
                else:
                    # ignore non-list mapping into child rows
                    continue
            else:
                # generic nested not supported in MVP
                continue
        else:
            out[tgt] = val

    if items_acc:
        out["items"] = items_acc
    return out


def apply_mapping_template(target_doctype: str, mapped: Dict[str, Any], mapping_template: Optional[str]) -> Dict[str, Any]:
    """Apply mapping template defaults and optional schema validator."""
    if not mapping_template:
        return mapped

    mt = frappe.get_doc("AI Mapping Template", mapping_template)
    if not mt.active:
        return mapped

    # defaults from json_schema if it contains a 'defaults' dict (lightweight)
    # this is intentionally minimal to keep template editable without complex child tables
    defaults = {}
    try:
        schema = json.loads(mt.json_schema or "{}")
        defaults = (schema.get("defaults") or {}) if isinstance(schema, dict) else {}
    except Exception:
        defaults = {}

    out = dict(defaults)
    out.update(mapped)

    # Basic coercions for known doctypes
    if target_doctype == "Purchase Order":
        # supplier field
        if out.get("supplier") and not out.get("supplier_name"):
            pass

    return out


def validate_for_doctype(target_doctype: str, doc_dict: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Best-effort validation. Returns (ok, errors)."""
    errors: List[str] = []
    meta = frappe.get_meta(target_doctype)

    # Required fields check
    for df in meta.fields:
        if df.reqd and df.fieldname:
            if df.fieldtype in ("Section Break", "Column Break", "Tab Break"):
                continue
            if doc_dict.get(df.fieldname) in (None, ""):
                errors.append(_("Missing required field: {0}").format(df.label or df.fieldname))

    # Child table items validation for PO
    if target_doctype == "Purchase Order":
        if not doc_dict.get("supplier"):
            errors.append(_("Missing Supplier"))
        if not doc_dict.get("items") or not isinstance(doc_dict.get("items"), list):
            errors.append(_("Missing Items table"))

    if target_doctype == "Employee":
        if not doc_dict.get("employee_name") and not doc_dict.get("first_name"):
            errors.append(_("Missing Employee Name"))
    return (len(errors) == 0, errors)
