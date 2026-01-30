# Install Notes (Frappe Cloud)

If you use **On‑Prem OCR**:
- Python packages: `pytesseract`, `Pillow`
- System binary: `tesseract` (and language packs)

Frappe Cloud environments may not include `tesseract` by default.
If your plan/environment cannot install system packages, use **Azure OCR** option.

Azure OCR requires:
- AZURE_FORM_RECOGNIZER_ENDPOINT
- AZURE_FORM_RECOGNIZER_KEY
