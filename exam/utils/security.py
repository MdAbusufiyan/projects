import re
import ipaddress
from functools import wraps
from flask import session, redirect, url_for, request, abort
from flask_login import current_user

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def valid_email(email):
    return bool(email) and bool(EMAIL_RE.match(email.strip()))

def sanitize_text(value, max_len=1000):
    if value is None:
        return ""
    value = str(value).strip()
    return value[:max_len]

def ip_in_restriction(ip, restriction_str):
    if not restriction_str:
        return True
    allowed = [r.strip() for r in restriction_str.split(",") if r.strip()]
    if not allowed:
        return True
    try:
        client_ip = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for rule in allowed:
        try:
            if "/" in rule:
                if client_ip in ipaddress.ip_network(rule, strict=False):
                    return True
            else:
                if client_ip == ipaddress.ip_address(rule):
                    return True
        except ValueError:
            continue
    return False

def professor_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not str(current_user.get_id()).startswith("prof:"):
            return redirect(url_for("auth.professor_login"))
        return f(*args, **kwargs)
    return wrapper

def get_client_ip():
    if request.headers.get("CF-Connecting-IP"):
        return request.headers.get("CF-Connecting-IP")
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr
