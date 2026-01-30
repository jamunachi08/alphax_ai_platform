# Copyright (c) 2026, AlphaX
# License: MIT (see LICENSE)

from __future__ import annotations

import io
import json
import os
from typing import Any, Dict, Tuple, Optional

import frappe


def _read_file_bytes(file_doc) -> bytes:
    if getattr(file_doc, "is_private", 0):
        path = frappe.get_site_path("private", "files", file_doc.file_name)
    else:
        path = frappe.get_site_path("public", "files", file_doc.file_name)

    with open(path, "rb") as f:
        return f.read()


def detect_mime_and_ext(file_doc) -> Tuple[str, str]:
    name = (file_doc.file_name or "").lower()
    ext = "." + name.split(".")[-1] if "." in name else ""
    mime = (file_doc.content_type or "").lower()

    if not mime:
        if ext in [".pdf"]:
            mime = "application/pdf"
        elif ext in [".png"]:
            mime = "image/png"
        elif ext in [".jpg", ".jpeg"]:
            mime = "image/jpeg"
        elif ext in [".xlsx"]:
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif ext in [".xls"]:
            mime = "application/vnd.ms-excel"
        elif ext in [".csv"]:
            mime = "text/csv"
        else:
            mime = "application/octet-stream"

    return mime, ext


def extract_from_pdf_text(file_bytes: bytes) -> Dict[str, Any]:
    try:
        import PyPDF2  # type: ignore
    except Exception:
        frappe.throw("PyPDF2 is required to extract text from PDFs. Install: pip install PyPDF2")

    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    texts = []
    for page in reader.pages:
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        if t:
            texts.append(t)

    return {"text": "\n\n".join(texts).strip(), "pages": len(reader.pages), "tables": [], "meta": {"mode": "pdf_text"}}


def extract_from_excel(file_bytes: bytes, ext: str) -> Dict[str, Any]:
    try:
        import pandas as pd  # type: ignore
    except Exception:
        frappe.throw("pandas is required for Excel extraction. Install: pip install pandas openpyxl")

    bio = io.BytesIO(file_bytes)
    if ext == ".csv":
        df = pd.read_csv(bio)
    else:
        df = pd.read_excel(bio)

    df = df.where(df.notna(), None)
    records = df.to_dict(orient="records")
    return {
        "text": "",
        "pages": 1,
        "tables": [{"name": "Sheet1", "rows": records}],
        "meta": {"mode": "excel", "columns": list(df.columns)},
    }


def extract_from_image_tesseract(file_bytes: bytes, language: str = "auto") -> Dict[str, Any]:
    try:
        from PIL import Image  # type: ignore
    except Exception:
        frappe.throw("Pillow is required for OCR on images. Install: pip install pillow")

    try:
        import pytesseract  # type: ignore
    except Exception:
        frappe.throw("pytesseract is required for OCR. Install: pip install pytesseract and OS tesseract binary")

    img = Image.open(io.BytesIO(file_bytes))
    lang = None
    if language in ("en", "ar"):
        lang = language
    try:
        text = pytesseract.image_to_string(img, lang=lang) if lang else pytesseract.image_to_string(img)
    except TypeError:
        text = pytesseract.image_to_string(img)

    return {"text": (text or "").strip(), "pages": 1, "tables": [], "meta": {"mode": "ocr_onprem"}}


def extract_with_azure_form_recognizer(file_bytes: bytes, mime: str) -> Dict[str, Any]:
    """Option A: Azure Form Recognizer (Document Intelligence).

    Env vars expected:
      - AZURE_FORM_RECOGNIZER_ENDPOINT  (e.g. https://xxxxx.cognitiveservices.azure.com)
      - AZURE_FORM_RECOGNIZER_KEY
    """
    try:
        import requests  # type: ignore
    except Exception:
        frappe.throw("requests is required for Azure OCR. Install: pip install requests")

    endpoint = os.environ.get("AZURE_FORM_RECOGNIZER_ENDPOINT") or ""
    key = os.environ.get("AZURE_FORM_RECOGNIZER_KEY") or ""
    if not endpoint or not key:
        frappe.throw("Azure OCR not configured. Set AZURE_FORM_RECOGNIZER_ENDPOINT and AZURE_FORM_RECOGNIZER_KEY")

    # Use prebuilt-read to keep it generic across document types
    url = endpoint.rstrip("/") + "/formrecognizer/documentModels/prebuilt-read:analyze?api-version=2023-07-31"
    headers = {"Ocp-Apim-Subscription-Key": key, "Content-Type": mime}
    r = requests.post(url, headers=headers, data=file_bytes, timeout=90)
    if r.status_code not in (200, 201, 202):
        frappe.throw(f"Azure OCR request failed: {r.status_code} {r.text}")

    # Azure is async; polling via Operation-Location
    op = r.headers.get("operation-location") or r.headers.get("Operation-Location")
    if not op:
        # Some endpoints may return result directly
        data = r.json()
        return {"text": json.dumps(data, ensure_ascii=False), "pages": 1, "tables": [], "meta": {"mode": "ocr_azure_raw"}}

    for _ in range(30):
        pr = requests.get(op, headers={"Ocp-Apim-Subscription-Key": key}, timeout=60)
        data = pr.json()
        status = (data.get("status") or "").lower()
        if status in ("succeeded", "failed"):
            if status == "failed":
                frappe.throw(f"Azure OCR analyze failed: {json.dumps(data, ensure_ascii=False)[:800]}")
            # Extract lines into text
            text_lines = []
            analyze = (data.get("analyzeResult") or {})
            for page in (analyze.get("pages") or []):
                for line in (page.get("lines") or []):
                    if line.get("content"):
                        text_lines.append(line["content"])
            return {
                "text": "\n".join(text_lines).strip(),
                "pages": len(analyze.get("pages") or []) or 1,
                "tables": analyze.get("tables") or [],
                "meta": {"mode": "ocr_azure", "raw_status": data.get("status")},
            }
        frappe.sleep(0.5)

    frappe.throw("Azure OCR timed out while polling analyze result")


def extract_content(file_doc, ocr_engine: str = "On-Prem", language: str = "auto") -> Dict[str, Any]:
    """Extract content from File using either:
      - Option A: Azure (cloud OCR)
      - Option B: On-Prem (tesseract OCR)
    """
    file_bytes = _read_file_bytes(file_doc)
    mime, ext = detect_mime_and_ext(file_doc)

    # Excel/CSV
    if ext in [".xlsx", ".xls", ".csv"]:
        return extract_from_excel(file_bytes, ext)

    # PDFs: try digital text first
    if mime == "application/pdf":
        pdf = extract_from_pdf_text(file_bytes)
        if pdf.get("text"):
            return pdf
        # scanned PDF: OCR only if Azure is chosen in this phase
        if (ocr_engine or "").lower().startswith("azure"):
            return extract_with_azure_form_recognizer(file_bytes, mime)
        return {"text": "", "pages": pdf.get("pages") or 1, "tables": [], "meta": {"mode": "pdf_scanned_unhandled"}}

    # Images: OCR
    if mime.startswith("image/"):
        if (ocr_engine or "").lower().startswith("azure"):
            return extract_with_azure_form_recognizer(file_bytes, mime)
        return extract_from_image_tesseract(file_bytes, language=language)

    # fallback: treat as text
    try:
        text = file_bytes.decode("utf-8", errors="ignore").strip()
    except Exception:
        text = ""
    return {"text": text, "pages": 1, "tables": [], "meta": {"mode": "raw"}}
