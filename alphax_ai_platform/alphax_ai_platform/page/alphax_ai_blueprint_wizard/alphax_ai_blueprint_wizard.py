import frappe

def get_context(context):
    # No server-side context required; handled by JS.
    context.no_cache = 1
