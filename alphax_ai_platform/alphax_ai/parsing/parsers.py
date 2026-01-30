from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import frappe


_DATE_PATTERNS = [
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d.%m.%Y",
]


def _parse_date(s: str) -> Optional[str]:
    s = (s or "").strip()
    if not s:
        return None
    # common cleanup
    s2 = re.sub(r"[^0-9/\-.]", "", s)
    for fmt in _DATE_PATTERNS:
        try:
            dt = datetime.strptime(s2, fmt).date()
            return dt.isoformat()
        except Exception:
            continue
    return None


def _find_first(patterns: List[str], text: str) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return (m.group(1) or "").strip()
    return None


def _extract_tables_as_rows(tables: List[Any]) -> List[Dict[str, Any]]:
    """Normalize tables coming from extractors. Expected format:
    - excel extractor returns: [{"type":"excel","rows":[{...}, ...]}]
    - pdf/image extractors may return [] or arbitrary.
    """
    rows: List[Dict[str, Any]] = []
    for t in (tables or []):
        if isinstance(t, dict) and isinstance(t.get("rows"), list):
            for r in t.get("rows"):
                if isinstance(r, dict):
                    rows.append(r)
    return rows


def parse_purchase_order(extracted_text: str, tables: List[Any], language: str = "auto") -> Dict[str, Any]:
    """Heuristic parser for Purchase Order-like documents (vendor quote / PO draft / proforma).
    Returns a canonical intermediate structure (not ERP fieldnames yet).
    """
    text = extracted_text or ""
    # Supplier
    supplier = _find_first([
        r"Supplier\s*[:\-]\s*(.+)",
        r"Vendor\s*[:\-]\s*(.+)",
        r"From\s*[:\-]\s*(.+)",
    ], text)

    # Dates
    trx_date = _parse_date(_find_first([r"Date\s*[:\-]\s*([0-9/\-.]+)", r"PO\s*Date\s*[:\-]\s*([0-9/\-.]+)"], text) or "")
    delivery_date = _parse_date(_find_first([r"Delivery\s*Date\s*[:\-]\s*([0-9/\-.]+)", r"Expected\s*Date\s*[:\-]\s*([0-9/\-.]+)"], text) or "")

    currency = _find_first([r"Currency\s*[:\-]\s*([A-Z]{3})"], text)

    # Items from tables (preferred)
    items: List[Dict[str, Any]] = []
    rows = _extract_tables_as_rows(tables)
    if rows:
        # attempt to find columns
        # accepted column aliases
        col_item = _pick_key(rows[0].keys(), ["item_code", "item", "description", "product", "name"])
        col_qty = _pick_key(rows[0].keys(), ["qty", "quantity", "q'ty", "qnty"])
        col_rate = _pick_key(rows[0].keys(), ["rate", "price", "unit_price", "unit price", "unitprice"])
        col_uom = _pick_key(rows[0].keys(), ["uom", "unit", "unit_of_measure"])
        col_amount = _pick_key(rows[0].keys(), ["amount", "total", "line_total", "line total"])
        for r in rows:
            desc = (r.get(col_item) if col_item else None) or ""
            if not str(desc).strip():
                continue
            it = {
                "description": str(desc).strip(),
                "qty": _to_float(r.get(col_qty)) if col_qty else None,
                "rate": _to_float(r.get(col_rate)) if col_rate else None,
                "uom": str(r.get(col_uom)).strip() if col_uom and r.get(col_uom) is not None else None,
                "amount": _to_float(r.get(col_amount)) if col_amount else None,
            }
            items.append({k: v for k, v in it.items() if v not in (None, "")})
    else:
        # fallback: parse simple line items from text (best-effort)
        # e.g. "1  ITEM NAME   10  5.00  50.00"
        for line in text.splitlines():
            line2 = line.strip()
            if not line2 or len(line2) < 10:
                continue
            m = re.match(r"^(\d+)\s+(.+?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)$", line2)
            if m:
                items.append({
                    "description": m.group(2).strip(),
                    "qty": _to_float(m.group(3)),
                    "rate": _to_float(m.group(4)),
                    "amount": _to_float(m.group(5)),
                })

    return {
        "doc_type": "purchase_order",
        "supplier": supplier,
        "transaction_date": trx_date,
        "schedule_date": delivery_date,
        "currency": currency,
        "items": items,
        "raw_excerpt": text[:2500],
    }


def parse_employee(extracted_text: str, tables: List[Any], language: str = "auto") -> Dict[str, Any]:
    """Heuristic parser for Employee profile documents (passport/iqama/cv summary forms)."""
    text = extracted_text or ""

    full_name = _find_first([
        r"Name\s*[:\-]\s*(.+)",
        r"Employee\s*Name\s*[:\-]\s*(.+)",
        r"Full\s*Name\s*[:\-]\s*(.+)",
    ], text)

    nationality = _find_first([r"Nationality\s*[:\-]\s*(.+)"], text)
    gender = _find_first([r"Gender\s*[:\-]\s*(Male|Female)"], text)
    dob = _parse_date(_find_first([r"Date\s*of\s*Birth\s*[:\-]\s*([0-9/\-.]+)", r"DOB\s*[:\-]\s*([0-9/\-.]+)"], text) or "")
    joining = _parse_date(_find_first([r"Joining\s*Date\s*[:\-]\s*([0-9/\-.]+)"], text) or "")
    mobile = _find_first([r"Mobile\s*[:\-]\s*([+0-9\s\-]{8,})", r"Phone\s*[:\-]\s*([+0-9\s\-]{8,})"], text)
    email = _find_first([r"Email\s*[:\-]\s*([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})"], text)

    national_id = _find_first([
        r"National\s*ID\s*[:\-]\s*([0-9]{6,})",
        r"Iqama\s*No\s*[:\-]\s*([0-9]{6,})",
        r"ID\s*No\s*[:\-]\s*([0-9]{6,})",
    ], text)

    designation = _find_first([r"Designation\s*[:\-]\s*(.+)", r"Job\s*Title\s*[:\-]\s*(.+)"], text)

    return {
        "doc_type": "employee",
        "employee_name": full_name,
        "nationality": nationality,
        "gender": gender,
        "date_of_birth": dob,
        "date_of_joining": joining,
        "cell_number": mobile,
        "personal_email": email,
        "national_id": national_id,
        "designation": designation,
        "raw_excerpt": text[:2500],
    }


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        s = str(v).strip()
        if not s:
            return None
        s = s.replace(",", "")
        return float(s)
    except Exception:
        return None


def _pick_key(keys, aliases: List[str]) -> Optional[str]:
    lower = {str(k).strip().lower(): k for k in keys}
    for a in aliases:
        if a.lower() in lower:
            return lower[a.lower()]
    # loose matching
    for a in aliases:
        for lk, orig in lower.items():
            if a.lower().replace("_", " ") in lk.replace("_", " "):
                return orig
    return None
