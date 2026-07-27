import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, bcrypt, limiter
from models.models import Professor
from utils.security import valid_email, sanitize_text, get_client_ip
from utils.logging_util import log_activity

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/professor/register", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def professor_register():
    if request.method == "POST":
        name = sanitize_text(request.form.get("name"), 120)
        email = sanitize_text(request.form.get("email"), 255).lower()
        password = request.form.get("password", "")

        if not name or not valid_email(email) or len(password) < 8:
            flash("Please provide valid name, email, and a password of at least 8 characters.", "error")
            return render_template("professor/register.html")

        if Professor.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "error")
            return render_template("professor/register.html")

        prof = Professor(name=name, email=email)
        prof.set_password(password)
        db.session.add(prof)
        db.session.commit()
        log_activity("professor", prof.id, "registered", get_client_ip())
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("auth.professor_login"))

    return render_template("professor/register.html")


@auth_bp.route("/professor/login", methods=["GET", "POST"])
@limiter.limit("15 per hour")
def professor_login():
    if request.method == "POST":
        email = sanitize_text(request.form.get("email"), 255).lower()
        password = request.form.get("password", "")

        prof = Professor.query.filter_by(email=email).first()
        if prof and prof.check_password(password):
            login_user(prof)
            session.permanent = True
            log_activity("professor", prof.id, "logged in", get_client_ip())
            return redirect(url_for("professor.dashboard"))

        flash("Invalid email or password.", "error")
        return render_template("professor/login.html")

    return render_template("professor/login.html")


@auth_bp.route("/professor/logout")
@login_required
def professor_logout():
    log_activity("professor", current_user.id, "logged out", get_client_ip())
    logout_user()
    return redirect(url_for("auth.professor_login"))
