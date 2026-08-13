import os
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user
from config import Config
from extensions import db, socketio, csrf, limiter, bcrypt, login_manager, mail
from models.models import Professor, Candidate
from routes.professor import professor_bp
from routes.candidate import candidate_bp
from sockets.events import register_socket_events


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    socketio.init_app(app)

    login_manager.login_view = None

    @login_manager.user_loader
    def load_user(user_id):
        if user_id.startswith("prof:"):
            return Professor.query.get(user_id.split(":", 1)[1])
        return None

    app.register_blueprint(professor_bp)
    app.register_blueprint(candidate_bp)
    csrf.exempt(candidate_bp)  # candidate API uses token-based session auth; CSRF handled via custom header check

    @app.before_request
    def use_workspace_professor():
        """Temporary single-workspace access while professor auth is disabled."""
        if request.blueprint != "professor":
            return None

        professor = Professor.query.order_by(Professor.created_at).first()
        if professor is None:
            professor = Professor(name="Workspace Owner", email="workspace-owner@local")
            professor.set_password(os.urandom(32).hex())
            db.session.add(professor)
            db.session.commit()

        login_user(professor, force=True)
        return None

    register_socket_events()

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        # PDFs are intentionally embedded only by pages on this same site.
        # DENY blocks even same-origin iframes and leaves the preview blank.
        if request.endpoint in {"professor.case_study_pdf", "candidate.case_study_pdf"}:
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
        else:
            response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

    @app.route("/")
    def index():
        return redirect(url_for("professor.dashboard"))

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("errors/413.html"), 413

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=8520, debug=False)
