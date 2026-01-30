from __future__ import annotations

import json
from typing import Any, Dict, Optional

import frappe
from frappe import _

from alphax_ai_platform.alphax_ai.ingestion.extractors import extract_content
from alphax_ai_platform.alphax_ai.parsing.parsers import (
    parse_purchase_order,
    parse_employee,
)
from alphax_ai_platform.alphax_ai.mapping.engine import (
    apply_schema_field_mapping,
    apply_mapping_template,
    validate_for_doctype,
)


def _get_file_doc(file_url: Optional[str], file_name: Optional[str]):
    if file_url:
        return frappe.get_doc("File", {"file_url": file_url})
    if file_name:
        return frappe.get_doc("File", {"file_name": file_name})
    frappe.throw(_("file_url or file_name is required"))


def _create_ingested_doc(file_doc, target_doctype, blueprint, ocr_engine, language_hint):
    ing = frappe.get_doc(
        {
            "doctype": "AI Ingested Document",
            "source_file": file_doc.name,
            "file_name": file_doc.file_name,
            "file_url": file_doc.file_url,
            "content_type": file_doc.content_type,
            "target_doctype": target_doctype,
            "blueprint": blueprint,
            "ocr_engine": ocr_engine,
            "language_hint": language_hint,
            "status": "Extracted",
        }
    )
    ing.insert(ignore_permissions=False)
    return ing.name


def _create_ocr_result(ingested_name, extracted):
    res = frappe.get_doc(
        {
            "doctype": "AI OCR Result",
            "ingested_document": ingested_name,
            "extracted_text": extracted.get("text") or "",
            "extracted_tables_json": json.dumps(
                extracted.get("tables") or [], ensure_ascii=False
            ),
            "extraction_meta_json": json.dumps(
                extracted.get("meta") or {}, ensure_ascii=False
            ),
            "pages": extracted.get("pages") or 1,
        }
    )
    res.insert(ignore_permissions=False)
    return res.name


def _safe_fallback_doc(target_doctype, extracted):
    return {
        "doctype": target_doctype,
        "alphax_ai_source_summary": (extracted.get("text") or "")[:1400],
    }


def _create_draft_doc(target_doctype, doc_dict):
    doc_dict["doctype"] = target_doctype
    doc = frappe.get_doc(doc_dict)
    doc.insert(ignore_permissions=False)
    return doc.name


def _resolve_blueprint(blueprint_name, target_doctype):
    if not blueprint_name:
        return {
            "target_doctype": target_doctype,
            "ocr_engine": "On-Prem",
            "language_hint": "auto",
            "schema_fields": [],
            "mapping_template": None,
            "blueprint": None,
        }

    bp = frappe.get_doc("AI Intake Blueprint", blueprint_name)
    return {
        "blueprint": bp.name,
        "target_doctype": bp.target_doctype,
        "ocr_engine": bp.default_ocr_engine or "On-Prem",
        "language_hint": bp.language_hint or "auto",
        "schema_fields": bp.get("schema_fields") or [],
        "mapping_template": bp.mapping_template,
    }


@frappe.whitelist()
def ingest_file(
    file_url=None,
    file_name=None,
    target_doctype="Sales Order",
    create_draft=1,
    mapping_template=None,
    blueprint_name=None,
):
    if not frappe.has_permission("File", "read"):
        frappe.throw(_("Not permitted to read File"))

    file_doc = _get_file_doc(file_url, file_name)

    bp = _resolve_blueprint(blueprint_name, target_doctype)
    target_doctype = bp.get("target_doctype") or target_doctype

    ingested_name = _create_ingested_doc(
        file_doc,
        target_doctype,
        bp.get("blueprint"),
        bp.get("ocr_engine"),
        bp.get("language_hint"),
    )

    extracted = extract_content(
        file_doc,
        ocr_engine=bp.get("ocr_engine"),
        language=bp.get("language_hint"),
    )

    ocr_name = _create_ocr_result(ingested_name, extracted)

    created_docname = None
    action_request = None

    if int(create_draft) == 1:
        parsed = None
        tables = extracted.get("tables") or []

        if bp.get("schema_fields"):
            if target_doctype == "Purchase Order":
                parsed = parse_purchase_order(extracted.get("text") or "", tables)
            elif target_doctype == "Employee":
                parsed = parse_employee(extracted.get("text") or "", tables)

        if parsed:
            doc_dict = apply_schema_field_mapping(parsed, bp.get("schema_fields"))
            doc_dict = apply_mapping_template(
                target_doctype,
                doc_dict,
                bp.get("mapping_template") or mapping_template,
            )
        else:
            doc_dict = _safe_fallback_doc(target_doctype, extracted)

        ok, errors = validate_for_doctype(target_doctype, doc_dict)

        if not ok or not frappe.has_permission(target_doctype, "create"):
            ar = frappe.get_doc(
                {
                    "doctype": "AI Action Request",
                    "action_type": "Create Draft",
                    "target_doctype": target_doctype,
                    "status": "Pending",
                    "source_ingested_document": ingested_name,
                    "payload_json": json.dumps(doc_dict, ensure_ascii=False),
                    "notes": "\n".join(errors or []),
                }
            )
            ar.insert(ignore_permissions=False)
            action_request = ar.name
        else:
            created_docname = _create_draft_doc(target_doctype, doc_dict)
            frappe.db.set_value(
                "AI Ingested Document",
                ingested_name,
                "created_document",
                created_docname,
            )

    return {
        "ok": True,
        "ingested_document": ingested_name,
        "ocr_result": ocr_name,
        "created_document": created_docname,
        "action_request": action_request,
    }
