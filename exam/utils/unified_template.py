import os
import json
from flask import request, current_app, render_template as flask_render_template


def _get_unified_context(template_name, **kwargs):
    base_context = {
        "request": request,
        "current_path": request.path,
        "template_name": template_name,
        "app_name": "Exam Platform",
        "page_title": "Exam Platform",
        "page_subtitle": "Secure exam delivery and monitoring",
        "show_nav": True,
    }
    base_context.update(kwargs)
    return base_context


def render_unified_template(template_name, **kwargs):
    if template_name.startswith("professor/") or template_name.startswith("candidate/"):
        page_title = template_name.replace("/", " ").replace(".html", "").title()
        kwargs.setdefault("page_title", page_title)
        kwargs.setdefault("page_subtitle", "Managed through the unified exam interface")
    elif template_name == "index.html":
        kwargs.setdefault("page_title", "Dashboard")
        kwargs.setdefault("page_subtitle", "Secure exam workspace")
    elif template_name == "errors/404.html":
        kwargs.setdefault("page_title", "Page Not Found")
        kwargs.setdefault("page_subtitle", "The requested page could not be found")
    elif template_name == "errors/413.html":
        kwargs.setdefault("page_title", "Upload Too Large")
        kwargs.setdefault("page_subtitle", "The request exceeded the configured limit")

    context = _get_unified_context(template_name, **kwargs)
    return flask_render_template("unified_layout.html", **context)
