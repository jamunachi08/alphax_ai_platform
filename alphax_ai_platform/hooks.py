app_name = "alphax_ai_platform"
app_title = "AlphaX AI"
app_publisher = "AlphaX"
app_description = "Enterprise-grade AI Operating System for ERPNext/Frappe"
app_email = "support@alphax.ai"
app_license = "MIT"

# Load JS/CSS for the Desk Page (Assistant)
app_include_js = ["/assets/alphax_ai_platform/js/ai_assistant.js"]
app_include_css = ["/assets/alphax_ai_platform/css/ai_assistant.css", "/assets/alphax_ai_platform/css/blueprint_wizard.css"]

fixtures = [
    {"dt": "AI Mapping Template"},
    {"dt": "AI Intake Blueprint"},
]

scheduler_events = {}

doc_events = {}
