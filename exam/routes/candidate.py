import secrets
import datetime
import random
from flask import (Blueprint, render_template, request, redirect, url_for,
                    session, jsonify, flash, current_app, send_from_directory, abort)
from extensions import db, limiter, socketio
from models.models import Exam, Candidate, Question, Answer
from utils.security import valid_email, sanitize_text, ip_in_restriction, get_client_ip
from utils.logging_util import log_activity, log_violation
from utils.grading import grade_candidate

candidate_bp = Blueprint("candidate", __name__, url_prefix="/exam")


def _check_common_restrictions(exam, email):
    ip = get_client_ip()
    if exam.ip_restriction and not ip_in_restriction(ip, exam.ip_restriction):
        return False, "Your network/IP is not authorized for this exam."
    if exam.email_restriction_domain:
        domain = exam.email_restriction_domain.lstrip("@").lower()
        if not email.lower().endswith("@" + domain):
            return False, f"Only emails from @{domain} are permitted."
    return True, None


@candidate_bp.route("/<exam_id>/join", methods=["GET", "POST"])
@limiter.limit("30 per hour")
def join(exam_id):
    exam = Exam.query.get(exam_id)
    if not exam or exam.status not in ("scheduled", "live"):
        return render_template("candidate/unavailable.html")

    now = datetime.datetime.utcnow()
    if exam.scheduled_end and now > exam.scheduled_end:
        return render_template("candidate/unavailable.html", message="This exam has ended.")

    token = request.args.get("token") or request.form.get("token")

    if request.method == "POST":
        name = sanitize_text(request.form.get("name"), 255)
        email = sanitize_text(request.form.get("email"), 255).lower()
        password = request.form.get("password", "")

        if not name or not valid_email(email):
            flash("Please provide a valid name and email.", "error")
            return render_template("candidate/join.html", exam=exam, token=token)

        ok, err = _check_common_restrictions(exam, email)
        if not ok:
            flash(err, "error")
            return render_template("candidate/join.html", exam=exam, token=token)

        candidate = None

        if exam.access_mode == "invite":
            candidate = Candidate.query.filter_by(exam_id=exam.id, access_token=token).first()
            if not candidate or candidate.email.lower() != email.lower():
                flash("Invalid or expired invite link.", "error")
                return render_template("candidate/join.html", exam=exam, token=token)

        elif exam.access_mode == "password":
            if password != exam.exam_password:
                flash("Incorrect exam password.", "error")
                return render_template("candidate/join.html", exam=exam, token=token)
            candidate = Candidate.query.filter_by(exam_id=exam.id, email=email).first()
            if not candidate:
                if Candidate.query.filter_by(exam_id=exam.id).count() >= exam.max_candidates:
                    flash("Maximum candidate limit reached for this exam.", "error")
                    return render_template("candidate/join.html", exam=exam, token=token)
                candidate = Candidate(exam_id=exam.id, name=name, email=email, access_token=secrets.token_urlsafe(32))
                db.session.add(candidate)

        else:  # open
            candidate = Candidate.query.filter_by(exam_id=exam.id, email=email).first()
            if not candidate:
                if Candidate.query.filter_by(exam_id=exam.id).count() >= exam.max_candidates:
                    flash("Maximum candidate limit reached for this exam.", "error")
                    return render_template("candidate/join.html", exam=exam, token=token)
                candidate = Candidate(exam_id=exam.id, name=name, email=email, access_token=secrets.token_urlsafe(32))
                db.session.add(candidate)

        if candidate.status in ("submitted", "terminated", "barred"):
            flash("This exam has already been completed or access was revoked.", "error")
            return render_template("candidate/join.html", exam=exam, token=token)

        session_token = secrets.token_urlsafe(24)
        candidate.session_token = session_token
        candidate.ip_address = get_client_ip()
        db.session.commit()

        session["candidate_id"] = candidate.id
        session["candidate_session_token"] = session_token
        session.permanent = True

        log_activity("candidate", candidate.id, "joined exam", get_client_ip())
        return redirect(url_for("candidate.exam_room", exam_id=exam.id))

    return render_template("candidate/join.html", exam=exam, token=token)


def _get_active_candidate(exam_id):
    cand_id = session.get("candidate_id")
    if not cand_id:
        return None
    candidate = Candidate.query.filter_by(id=cand_id, exam_id=exam_id).first()
    if not candidate:
        return None
    if candidate.session_token != session.get("candidate_session_token"):
        return None
    return candidate


@candidate_bp.route("/<exam_id>/room")
def exam_room(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    candidate = _get_active_candidate(exam_id)
    if not candidate:
        return redirect(url_for("candidate.join", exam_id=exam_id))

    if candidate.status in ("submitted", "terminated", "barred"):
        return render_template("candidate/result.html", exam=exam, candidate=candidate)

    if candidate.status == "not_started":
        candidate.status = "in_progress"
        candidate.start_time = datetime.datetime.utcnow()
        candidate.remaining_seconds = exam.duration_minutes * 60
        db.session.commit()

    questions = Question.query.filter_by(exam_id=exam.id).order_by(Question.order_index).all()
    q_list = list(questions)
    if exam.randomize_questions:
        rnd = random.Random(candidate.id)
        rnd.shuffle(q_list)

    serializable = []
    for q in q_list:
        opts = [("a", q.option_a), ("b", q.option_b)]
        if q.option_c:
            opts.append(("c", q.option_c))
        if q.option_d:
            opts.append(("d", q.option_d))
        if exam.randomize_options:
            rnd2 = random.Random(candidate.id + q.id)
            rnd2.shuffle(opts)
        existing = Answer.query.filter_by(candidate_id=candidate.id, question_id=q.id).first()
        serializable.append({
            "id": q.id,
            "text": q.question_text,
            "options": opts,
            "marks": q.marks,
            "selected": existing.selected_option if existing else None,
        })

    has_case_study = bool(exam.case_study_pdf)
    return render_template(
        "candidate/exam_room.html", exam=exam, candidate=candidate,
        questions=serializable, has_case_study=has_case_study,
    )


@candidate_bp.route("/<exam_id>/case-study.pdf")
def case_study_pdf(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    candidate = _get_active_candidate(exam_id)
    if not candidate or not exam.case_study_pdf:
        abort(404)
    import os
    directory = os.path.dirname(exam.case_study_pdf)
    filename = os.path.basename(exam.case_study_pdf)
    return send_from_directory(directory, filename)


@candidate_bp.route("/<exam_id>/api/answer", methods=["POST"])
def submit_answer(exam_id):
    candidate = _get_active_candidate(exam_id)
    if not candidate or candidate.status != "in_progress":
        return jsonify({"ok": False, "error": "invalid_session"}), 403

    data = request.get_json(silent=True) or {}
    question_id = data.get("question_id")
    selected = (data.get("selected") or "").lower()
    if selected not in ("a", "b", "c", "d", ""):
        return jsonify({"ok": False}), 400

    question = Question.query.filter_by(id=question_id, exam_id=exam_id).first()
    if not question:
        return jsonify({"ok": False}), 404

    ans = Answer.query.filter_by(candidate_id=candidate.id, question_id=question_id).first()
    if not ans:
        ans = Answer(candidate_id=candidate.id, question_id=question_id)
        db.session.add(ans)
    ans.selected_option = selected or None
    db.session.commit()

    socketio.emit("candidate_update", {
        "candidate_id": candidate.id, "field": "answer_saved", "question_id": question_id,
    }, room=f"monitor_{exam_id}")

    return jsonify({"ok": True})


@candidate_bp.route("/<exam_id>/api/navigate", methods=["POST"])
def navigate(exam_id):
    candidate = _get_active_candidate(exam_id)
    if not candidate or candidate.status != "in_progress":
        return jsonify({"ok": False}), 403
    data = request.get_json(silent=True) or {}
    candidate.current_question_index = int(data.get("index", 0))
    db.session.commit()
    socketio.emit("candidate_update", {
        "candidate_id": candidate.id, "field": "current_question", "value": candidate.current_question_index,
    }, room=f"monitor_{exam_id}")
    return jsonify({"ok": True})


@candidate_bp.route("/<exam_id>/api/heartbeat", methods=["POST"])
def heartbeat(exam_id):
    candidate = _get_active_candidate(exam_id)
    if not candidate or candidate.status != "in_progress":
        return jsonify({"ok": False}), 403

    data = request.get_json(silent=True) or {}
    remaining = data.get("remaining_seconds")
    if isinstance(remaining, int):
        candidate.remaining_seconds = remaining
    db.session.commit()

    exam = Exam.query.get(exam_id)
    if remaining is not None and remaining <= 0:
        candidate.status = "submitted"
        candidate.end_time = datetime.datetime.utcnow()
        db.session.commit()
        grade_candidate(candidate.id)
        socketio.emit("candidate_update", {"candidate_id": candidate.id, "field": "status", "value": "submitted"}, room=f"monitor_{exam_id}")
        return jsonify({"ok": True, "time_up": True})

    return jsonify({"ok": True})


@candidate_bp.route("/<exam_id>/api/violation", methods=["POST"])
def report_violation(exam_id):
    candidate = _get_active_candidate(exam_id)
    if not candidate or candidate.status != "in_progress":
        return jsonify({"ok": False}), 403

    exam = Exam.query.get(exam_id)
    anti_cheat = exam.anti_cheat
    data = request.get_json(silent=True) or {}
    vtype = sanitize_text(data.get("type"), 50)
    details = sanitize_text(data.get("details"), 500)

    log_violation(candidate.id, exam_id, vtype, details)

    if vtype == "tab_switch":
        candidate.tab_switch_count += 1
    elif vtype == "blur":
        candidate.blur_count += 1
    elif vtype == "fullscreen_exit":
        candidate.fullscreen_exit_count += 1

    action_taken = None
    if anti_cheat:
        exceeded_warnings = candidate.warnings_count >= anti_cheat.max_warnings
        exceeded_tabswitch = candidate.tab_switch_count >= anti_cheat.max_tab_switches
        if vtype in ("tab_switch", "blur", "fullscreen_exit", "copy", "paste", "right_click", "js_disabled"):
            candidate.warnings_count += 1

        if candidate.warnings_count >= anti_cheat.max_warnings or exceeded_tabswitch or vtype == "js_disabled":
            if anti_cheat.violation_action == "terminate" or vtype == "js_disabled":
                candidate.status = "terminated" if vtype != "js_disabled" else "barred"
                candidate.end_time = datetime.datetime.utcnow()
                action_taken = "terminated"
            elif anti_cheat.violation_action == "auto_submit":
                candidate.status = "submitted"
                candidate.end_time = datetime.datetime.utcnow()
                grade_candidate(candidate.id)
                action_taken = "auto_submit"

    db.session.commit()

    socketio.emit("candidate_update", {
        "candidate_id": candidate.id, "field": "violation",
        "violation_type": vtype, "warnings": candidate.warnings_count,
        "tab_switch_count": candidate.tab_switch_count, "blur_count": candidate.blur_count,
        "fullscreen_exit_count": candidate.fullscreen_exit_count,
        "status": candidate.status,
    }, room=f"monitor_{exam_id}")

    return jsonify({"ok": True, "action": action_taken, "warnings": candidate.warnings_count})


@candidate_bp.route("/<exam_id>/api/submit", methods=["POST"])
def submit_exam(exam_id):
    candidate = _get_active_candidate(exam_id)
    if not candidate or candidate.status != "in_progress":
        return jsonify({"ok": False}), 403

    candidate.status = "submitted"
    candidate.end_time = datetime.datetime.utcnow()
    db.session.commit()
    score = grade_candidate(candidate.id)

    socketio.emit("candidate_update", {
        "candidate_id": candidate.id, "field": "status", "value": "submitted", "score": score,
    }, room=f"monitor_{exam_id}")

    return jsonify({"ok": True, "score": score})
