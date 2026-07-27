import os
import csv
import io
import secrets
import datetime
import pandas as pd
from flask import (Blueprint, render_template, request, redirect, url_for,
                    flash, current_app, jsonify, send_file, abort)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db, limiter, socketio
from models.models import Exam, AntiCheatConfig, Question, Candidate, Answer, ViolationLog
from utils.security import professor_required, sanitize_text, valid_email, get_client_ip
from utils.files import validate_and_save, ALLOWED_PDF_MIME, ALLOWED_SHEET_MIME
from utils.pdf_parser import parse_mcq_pdf
from utils.mailer import send_invite_email
from utils.logging_util import log_activity
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas

professor_bp = Blueprint("professor", __name__, url_prefix="/professor")

MAX_CANDIDATES = 100
MAX_SCHEDULE_DAYS = 62


def _exam_or_404(exam_id):
    exam = Exam.query.filter_by(id=exam_id, professor_id=current_user.id).first()
    if not exam:
        abort(404)
    return exam


def _question_issues(question):
    """Return author-facing validation issues for one MCQ."""
    options = {
        "a": question.option_a,
        "b": question.option_b,
        "c": question.option_c,
        "d": question.option_d,
    }
    issues = []
    if not question.question_text or not question.question_text.strip():
        issues.append("Question text is missing")
    if not options["a"] or not options["b"]:
        issues.append("Options A and B are required")
    if question.correct_option not in options or not options.get(question.correct_option):
        issues.append("The marked correct answer has no matching option")
    return issues


@professor_bp.route("/dashboard")
@login_required
@professor_required
def dashboard():
    exams = Exam.query.filter_by(professor_id=current_user.id).order_by(Exam.created_at.desc()).all()
    grouped = {"draft": [], "scheduled": [], "live": [], "completed": []}
    for e in exams:
        grouped.setdefault(e.status, []).append(e)
    return render_template("professor/dashboard.html", grouped=grouped)


@professor_bp.route("/exams/create", methods=["GET", "POST"])
@login_required
@professor_required
def create_exam():
    if request.method == "POST":
        title = sanitize_text(request.form.get("title"), 255)
        description = sanitize_text(request.form.get("description"), 2000)
        access_mode = request.form.get("access_mode", "open")
        max_candidates = min(int(request.form.get("max_candidates", 100) or 100), MAX_CANDIDATES)
        duration_minutes = int(request.form.get("duration_minutes", 60) or 60)
        randomize_questions = request.form.get("randomize_questions") == "on"
        randomize_options = request.form.get("randomize_options") == "on"
        ip_restriction = sanitize_text(request.form.get("ip_restriction"), 1000)
        email_restriction_domain = sanitize_text(request.form.get("email_restriction_domain"), 255)

        if not title:
            flash("Exam title is required.", "error")
            return render_template("professor/create_exam.html")

        exam_password = None
        if access_mode == "password":
            exam_password = request.form.get("exam_password") or secrets.token_urlsafe(6)

        exam = Exam(
            professor_id=current_user.id,
            title=title,
            description=description,
            access_mode=access_mode,
            exam_password=exam_password,
            max_candidates=max_candidates,
            duration_minutes=duration_minutes,
            randomize_questions=randomize_questions,
            randomize_options=randomize_options,
            ip_restriction=ip_restriction,
            email_restriction_domain=email_restriction_domain,
            status="draft",
        )

        case_pdf = request.files.get("case_study_pdf")
        if case_pdf and case_pdf.filename:
            path, err = validate_and_save(
                case_pdf,
                os.path.join(current_app.config["UPLOAD_FOLDER"], "case_studies"),
                current_app.config["ALLOWED_PDF_EXT"],
                ALLOWED_PDF_MIME,
                current_app.config["MAX_CONTENT_LENGTH"],
            )
            if err:
                flash(f"Case study upload failed: {err}", "error")
                return render_template("professor/create_exam.html")
            exam.case_study_pdf = path

        db.session.add(exam)
        db.session.flush()

        anti_cheat = AntiCheatConfig(exam_id=exam.id)
        for field in [
            "disable_copy", "disable_paste", "disable_right_click", "disable_refresh",
            "disable_printing", "disable_drag_drop", "disable_text_selection",
            "require_fullscreen", "detect_tab_switch", "detect_window_blur",
            "detect_fullscreen_exit", "detect_multiple_login",
        ]:
            setattr(anti_cheat, field, request.form.get(field) == "on")
        anti_cheat.max_warnings = int(request.form.get("max_warnings", 3) or 3)
        anti_cheat.max_tab_switches = int(request.form.get("max_tab_switches", 3) or 3)
        anti_cheat.max_seconds_outside = int(request.form.get("max_seconds_outside", 30) or 30)
        anti_cheat.violation_action = request.form.get("violation_action", "warning")
        db.session.add(anti_cheat)

        mcq_pdf = request.files.get("mcq_pdf")
        parsed_question_count = None
        if mcq_pdf and mcq_pdf.filename:
            path, err = validate_and_save(
                mcq_pdf,
                os.path.join(current_app.config["UPLOAD_FOLDER"], "mcq"),
                current_app.config["ALLOWED_PDF_EXT"],
                ALLOWED_PDF_MIME,
                current_app.config["MAX_CONTENT_LENGTH"],
            )
            if err:
                flash(f"MCQ PDF upload failed: {err}", "error")
                return render_template("professor/create_exam.html")
            try:
                parsed = parse_mcq_pdf(path)
            except Exception:
                flash("The MCQ PDF could not be read. Use a text-based PDF and try again.", "error")
                return render_template("professor/create_exam.html")
            parsed_question_count = len(parsed)
            for idx, q in enumerate(parsed):
                db.session.add(Question(
                    exam_id=exam.id, question_text=q["question_text"],
                    option_a=q["option_a"], option_b=q["option_b"],
                    option_c=q["option_c"], option_d=q["option_d"],
                    correct_option=q["correct_option"], order_index=idx,
                ))

        db.session.commit()
        log_activity("professor", current_user.id, f"created exam {exam.id}", get_client_ip())
        if parsed_question_count is None:
            flash("Exam created. Add questions, then use Preview before scheduling.", "success")
        elif parsed_question_count:
            flash(f"Exam created. {parsed_question_count} MCQ(s) were imported; review them in Preview before scheduling.", "success")
        else:
            flash("Exam created, but no MCQs were found in the PDF. Use the documented Q1/A)/Answer: A format or add questions manually.", "warning")
        return redirect(url_for("professor.edit_exam", exam_id=exam.id))

    return render_template("professor/create_exam.html")


@professor_bp.route("/exams/<exam_id>/edit", methods=["GET"])
@login_required
@professor_required
def edit_exam(exam_id):
    exam = _exam_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam.id).order_by(Question.order_index).all()
    candidates = Candidate.query.filter_by(exam_id=exam.id).all()
    return render_template("professor/edit_exam.html", exam=exam, questions=questions, candidates=candidates)


@professor_bp.route("/exams/<exam_id>/preview")
@login_required
@professor_required
def preview_exam(exam_id):
    exam = _exam_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam.id).order_by(Question.order_index).all()
    validation = {q.id: _question_issues(q) for q in questions}
    return render_template("professor/preview_exam.html", exam=exam, questions=questions,
                           validation=validation)


@professor_bp.route("/exams/<exam_id>/live-preview")
@login_required
@professor_required
def live_preview(exam_id):
    """A safe, non-persistent rendition of the candidate exam interface."""
    exam = _exam_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam.id).order_by(Question.order_index).all()
    return render_template("professor/live_preview.html", exam=exam, questions=questions)


@professor_bp.route("/exams/<exam_id>/case-study.pdf")
@login_required
@professor_required
def case_study_pdf(exam_id):
    exam = _exam_or_404(exam_id)
    if not exam.case_study_pdf or not os.path.isfile(exam.case_study_pdf):
        abort(404)
    return send_file(exam.case_study_pdf, mimetype="application/pdf", as_attachment=False)


@professor_bp.route("/exams/<exam_id>/anti-cheat", methods=["POST"])
@login_required
@professor_required
def update_anti_cheat(exam_id):
    exam = _exam_or_404(exam_id)
    config = exam.anti_cheat
    if not config:
        config = AntiCheatConfig(exam_id=exam.id)
        db.session.add(config)

    fields = [
        "disable_copy", "disable_paste", "disable_right_click", "disable_refresh",
        "disable_printing", "disable_drag_drop", "disable_text_selection",
        "require_fullscreen", "detect_tab_switch", "detect_window_blur",
        "detect_fullscreen_exit", "detect_multiple_login",
    ]
    for field in fields:
        setattr(config, field, request.form.get(field) == "on")
    config.max_warnings = max(1, int(request.form.get("max_warnings", 3) or 3))
    config.max_tab_switches = max(1, int(request.form.get("max_tab_switches", 3) or 3))
    config.max_seconds_outside = max(5, int(request.form.get("max_seconds_outside", 30) or 30))
    config.violation_action = request.form.get("violation_action", "warning")
    db.session.commit()
    flash("Live-test protection settings updated.", "success")
    return redirect(url_for("professor.edit_exam", exam_id=exam.id))


@professor_bp.route("/exams/<exam_id>/delete", methods=["POST"])
@login_required
@professor_required
def delete_draft(exam_id):
    exam = _exam_or_404(exam_id)
    if exam.status != "draft":
        flash("Only draft exams can be deleted.", "error")
        return redirect(url_for("professor.dashboard"))
    db.session.delete(exam)
    db.session.commit()
    flash("Draft exam deleted.", "success")
    return redirect(url_for("professor.dashboard"))


@professor_bp.route("/exams/<exam_id>/questions/add", methods=["POST"])
@login_required
@professor_required
def add_question(exam_id):
    exam = _exam_or_404(exam_id)
    q = Question(
        exam_id=exam.id,
        question_text=sanitize_text(request.form.get("question_text"), 2000),
        option_a=sanitize_text(request.form.get("option_a"), 500),
        option_b=sanitize_text(request.form.get("option_b"), 500),
        option_c=sanitize_text(request.form.get("option_c"), 500),
        option_d=sanitize_text(request.form.get("option_d"), 500),
        correct_option=request.form.get("correct_option", "a").lower(),
        marks=float(request.form.get("marks", 1) or 1),
        order_index=Question.query.filter_by(exam_id=exam.id).count(),
    )
    db.session.add(q)
    db.session.commit()
    return jsonify({"ok": True, "question_id": q.id})


@professor_bp.route("/exams/<exam_id>/questions/import-pdf", methods=["POST"])
@login_required
@professor_required
def import_mcq_pdf(exam_id):
    exam = _exam_or_404(exam_id)
    if exam.status != "draft":
        flash("Questions can only be imported while the exam is a draft.", "error")
        return redirect(url_for("professor.edit_exam", exam_id=exam.id))

    mcq_pdf = request.files.get("mcq_pdf")
    path, err = validate_and_save(
        mcq_pdf,
        os.path.join(current_app.config["UPLOAD_FOLDER"], "mcq"),
        current_app.config["ALLOWED_PDF_EXT"], ALLOWED_PDF_MIME,
        current_app.config["MAX_CONTENT_LENGTH"],
    )
    if err:
        flash(f"MCQ PDF upload failed: {err}", "error")
        return redirect(url_for("professor.edit_exam", exam_id=exam.id))
    try:
        parsed = parse_mcq_pdf(path)
    except Exception:
        flash("The MCQ PDF could not be read. Please use a text-based PDF.", "error")
        return redirect(url_for("professor.edit_exam", exam_id=exam.id))
    if not parsed:
        flash("No valid MCQs were found. Check that each question has A and B options and an answer key.", "error")
        return redirect(url_for("professor.edit_exam", exam_id=exam.id))

    if request.form.get("replace_questions") == "on":
        Question.query.filter_by(exam_id=exam.id).delete()
    start_index = Question.query.filter_by(exam_id=exam.id).count()
    for offset, question in enumerate(parsed):
        db.session.add(Question(exam_id=exam.id, order_index=start_index + offset, **question))
    db.session.commit()
    flash(f"Imported {len(parsed)} MCQ(s). Review them in Preview before scheduling.", "success")
    return redirect(url_for("professor.preview_exam", exam_id=exam.id))


@professor_bp.route("/exams/<exam_id>/questions/<question_id>/delete", methods=["POST"])
@login_required
@professor_required
def delete_question(exam_id, question_id):
    exam = _exam_or_404(exam_id)
    Question.query.filter_by(id=question_id, exam_id=exam.id).delete()
    db.session.commit()
    return jsonify({"ok": True})


@professor_bp.route("/exams/<exam_id>/candidates/add", methods=["POST"])
@login_required
@professor_required
def add_candidates(exam_id):
    exam = _exam_or_404(exam_id)
    current_count = Candidate.query.filter_by(exam_id=exam.id).count()

    names = request.form.getlist("names[]")
    emails = request.form.getlist("emails[]")
    added = []
    for name, email in zip(names, emails):
        name = sanitize_text(name, 255)
        email = sanitize_text(email, 255).lower()
        if not name or not valid_email(email):
            continue
        if current_count + len(added) >= exam.max_candidates:
            break
        if Candidate.query.filter_by(exam_id=exam.id, email=email).first():
            continue
        cand = Candidate(
            exam_id=exam.id, name=name, email=email,
            access_token=secrets.token_urlsafe(32), invited=(exam.access_mode == "invite"),
        )
        db.session.add(cand)
        added.append(cand)

    sheet = request.files.get("candidate_sheet")
    if sheet and sheet.filename:
        path, err = validate_and_save(
            sheet, os.path.join(current_app.config["UPLOAD_FOLDER"], "invites"),
            current_app.config["ALLOWED_SHEET_EXT"], ALLOWED_SHEET_MIME,
            current_app.config["MAX_CONTENT_LENGTH"],
        )
        if not err:
            try:
                if path.endswith(".csv"):
                    df = pd.read_csv(path)
                else:
                    df = pd.read_excel(path)
                for _, row in df.iterrows():
                    if current_count + len(added) >= exam.max_candidates:
                        break
                    name = sanitize_text(row.get("Name") or row.get("name"), 255)
                    email = sanitize_text(row.get("Email") or row.get("email"), 255).lower()
                    if not name or not valid_email(email):
                        continue
                    if Candidate.query.filter_by(exam_id=exam.id, email=email).first():
                        continue
                    cand = Candidate(
                        exam_id=exam.id, name=name, email=email,
                        access_token=secrets.token_urlsafe(32), invited=(exam.access_mode == "invite"),
                    )
                    db.session.add(cand)
                    added.append(cand)
            except Exception as e:
                flash(f"Sheet parsing error: {e}", "error")

    db.session.commit()

    if exam.access_mode == "invite":
        base_url = request.host_url.rstrip("/")
        for cand in added:
            link = f"{base_url}/exam/{exam.id}/join?token={cand.access_token}"
            send_invite_email(cand.email, cand.name, exam.title, link, exam.exam_password)

    flash(f"Added {len(added)} candidate(s).", "success")
    return redirect(url_for("professor.edit_exam", exam_id=exam.id))


@professor_bp.route("/exams/<exam_id>/schedule", methods=["POST"])
@login_required
@professor_required
def schedule_exam(exam_id):
    exam = _exam_or_404(exam_id)
    start_str = request.form.get("scheduled_start")
    try:
        start = datetime.datetime.fromisoformat(start_str)
    except Exception:
        flash("Invalid start date/time.", "error")
        return redirect(url_for("professor.edit_exam", exam_id=exam.id))

    max_date = datetime.datetime.utcnow() + datetime.timedelta(days=MAX_SCHEDULE_DAYS)
    if start > max_date:
        flash("Exams can only be scheduled up to 2 months in advance.", "error")
        return redirect(url_for("professor.edit_exam", exam_id=exam.id))

    questions = Question.query.filter_by(exam_id=exam.id).all()
    if not questions:
        flash("Add at least one question before scheduling.", "error")
        return redirect(url_for("professor.edit_exam", exam_id=exam.id))
    invalid_count = sum(bool(_question_issues(question)) for question in questions)
    if invalid_count:
        flash(f"Fix {invalid_count} invalid question(s) shown in Preview before scheduling.", "error")
        return redirect(url_for("professor.preview_exam", exam_id=exam.id))

    exam.scheduled_start = start
    exam.scheduled_end = start + datetime.timedelta(minutes=exam.duration_minutes)
    exam.status = "scheduled"
    db.session.commit()
    log_activity("professor", current_user.id, f"scheduled exam {exam.id}", get_client_ip())
    flash("Exam scheduled successfully.", "success")
    return redirect(url_for("professor.dashboard"))


@professor_bp.route("/exams/<exam_id>/go-live", methods=["POST"])
@login_required
@professor_required
def go_live(exam_id):
    exam = _exam_or_404(exam_id)
    questions = Question.query.filter_by(exam_id=exam.id).all()
    if not questions or any(_question_issues(question) for question in questions):
        flash("Add valid questions and review Preview before going live.", "error")
        return redirect(url_for("professor.preview_exam", exam_id=exam.id))
    exam.status = "live"
    if not exam.scheduled_start:
        exam.scheduled_start = datetime.datetime.utcnow()
        exam.scheduled_end = exam.scheduled_start + datetime.timedelta(minutes=exam.duration_minutes)
    db.session.commit()
    return redirect(url_for("professor.monitor", exam_id=exam.id))


@professor_bp.route("/exams/<exam_id>/monitor")
@login_required
@professor_required
def monitor(exam_id):
    exam = _exam_or_404(exam_id)
    candidates = Candidate.query.filter_by(exam_id=exam.id).all()
    return render_template("professor/monitor.html", exam=exam, candidates=candidates)


@professor_bp.route("/exams/<exam_id>/export/csv")
@login_required
@professor_required
def export_csv(exam_id):
    exam = _exam_or_404(exam_id)
    candidates = Candidate.query.filter_by(exam_id=exam.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Email", "Status", "Score", "Warnings", "Tab Switches", "Blur Count", "Fullscreen Exits"])
    for c in candidates:
        writer.writerow([c.name, c.email, c.status, c.score, c.warnings_count, c.tab_switch_count, c.blur_count, c.fullscreen_exit_count])

    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name=f"{exam.title}_results.csv")


@professor_bp.route("/exams/<exam_id>/export/pdf")
@login_required
@professor_required
def export_pdf(exam_id):
    exam = _exam_or_404(exam_id)
    candidates = Candidate.query.filter_by(exam_id=exam.id).all()

    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, f"Results: {exam.title}")
    y -= 30
    c.setFont("Helvetica", 10)
    for cand in candidates:
        line = f"{cand.name} | {cand.email} | Status: {cand.status} | Score: {cand.score}"
        c.drawString(40, y, line)
        y -= 18
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=f"{exam.title}_results.pdf")
