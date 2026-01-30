# AlphaX AI Platform (alphax_ai_platform) — v0.5.1

An **AI automation layer** for **ERPNext / Frappe (v15+)** that enables users to:
- ingest PDFs / images / Excel files,
- extract text + tables using **On‑Prem OCR (default)** or **Azure Document Intelligence**,
- drive extraction and document creation using **Blueprints** (user-defined schemas + mappings),
- create **Draft** ERPNext documents (safe-by-design),
- route failures to **AI Action Request** for review/approval.

> Default OCR engine: **On‑Prem** (Tesseract via `pytesseract`, optional).  
> If On‑Prem dependencies are missing on your environment, the app will show a clear install/runtime message.

---

## 1) Key Features

### 1.1 OCR + Extraction (PDF/Image/Excel)
- **On‑Prem OCR** (default): `pytesseract` + `Pillow` (image OCR)
- **Azure OCR** (optional): Azure Document Intelligence (Form Recognizer)
- **Excel/CSV extraction** using `pandas` + `openpyxl`
- Returns a normalized output:
  - `text`
  - `tables` (rows for Excel; can be extended for PDFs)
  - `meta` (mode/engine)

### 1.2 Blueprint-Driven Automation (User-driven, not hardcoded)
- **AI Intake Blueprint**: defines:
  - target DocType (e.g., Purchase Order, Employee)
  - extraction mode (schema-first)
  - default OCR engine
  - language hint
  - schema fields (what to extract + mapping targets)
- **AI Mapping Template**: optional defaults and rules.

### 1.3 Parsing + Mapping (PO + Employee starter)
- Starter canonical parsers:
  - **Purchase Order** (supplier, dates, currency, items)
  - **Employee** (name, nationality, DOB, joining date, contacts)
- Mapping engine converts canonical keys into ERPNext fields based on Blueprint schema.

### 1.4 Safe Draft Creation + Approval Queue
- Never submits or posts entries automatically.
- If validation fails OR user lacks create permission:
  - creates **AI Action Request** with payload + notes
- If validation passes:
  - creates a **Draft** document (e.g., Purchase Order / Employee)

### 1.5 Auditability
- Ingested files tracked in **AI Ingested Document**
- OCR output stored in **AI OCR Result**
- Actions tracked in **AI Action Request**

---

## 2) Compatibility

- **ERPNext / Frappe:** v15+
- **Frappe Cloud:** supported  
  (Note: On‑Prem OCR may require system availability of `tesseract` binary. If not available, use Azure option.)

---

## 3) Installation (Bench / Frappe Cloud)

### 3.1 Install the app
```bash
bench get-app https://<your-repo>/alphax_ai_platform.git
bench --site <site-name> install-app alphax_ai_platform
bench restart
```

### 3.2 Optional Python dependencies (On‑Prem OCR + Excel)
If your environment allows installing python deps:
```bash
pip install pytesseract pillow pandas openpyxl
```

If you can install OS deps:
- Install **tesseract** binary and (optionally) Arabic language pack.

### 3.3 Azure OCR setup (optional)
Set environment variables:
- `AZURE_FORM_RECOGNIZER_ENDPOINT`
- `AZURE_FORM_RECOGNIZER_KEY`

---

## 4) How to Use

### 4.1 Create / review templates
After install, you will find:
- **AI Intake Blueprint** (templates)
- **AI Mapping Template** (templates)

Duplicate the templates and adjust mappings for your company setup.

### 4.2 Ingest a file and create draft
From Desk Console (or custom UI), call:

```js
frappe.call({
  method: "alphax_ai_platform.alphax_ai.api.ingest.ingest_file",
  args: {
    file_url: "/files/sample_po.pdf",
    blueprint_name: "Purchase Order Intake (Template)",
    create_draft: 1
  }
}).then(r => console.log(r.message));
```

**Response:**
- `created_document` → Draft document name (if created)
- `action_request` → created when validation/permissions block draft

### 4.3 Employee creation (template)
```js
frappe.call({
  method: "alphax_ai_platform.alphax_ai.api.ingest.ingest_file",
  args: {
    file_url: "/files/employee_profile.jpg",
    blueprint_name: "Employee Creation Intake (Template)",
    create_draft: 1
  }
});
```

---

## 5) Typical Setup Checklist (Production)

1. Decide OCR Engine:
   - On‑Prem for self-hosted / OCI where you can install tesseract
   - Azure for Frappe Cloud if system deps aren’t available
2. Duplicate blueprint templates:
   - map supplier strategy, item strategy, default company, taxes
3. Add HR custom fields:
   - `custom_iqama` / `custom_national_id` and update schema mapping
4. Create role-based permissions:
   - allow ingestion for operators
   - allow draft creation for managers
   - route to Action Requests otherwise

---

## 6) Support & Roadmap

Planned enhancements:
- Document preview + field-by-field review UI before insert
- Better PDF table extraction
- Master matching for Supplier/Item/Employee (fuzzy match with confidence)
- Guided onboarding wizard & tooltips across the UI

---
