import uuid
import datetime
from extensions import db, bcrypt
from flask_login import UserMixin

def gen_uuid():
    return str(uuid.uuid4())

class Professor(db.Model, UserMixin):
    __tablename__ = "professors"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = bcrypt.generate_password_hash(pw).decode("utf-8")

    def check_password(self, pw):
        return bcrypt.check_password_hash(self.password_hash, pw)

    def get_id(self):
        return f"prof:{self.id}"


class Exam(db.Model):
    __tablename__ = "exams"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    professor_id = db.Column(db.String(36), db.ForeignKey("professors.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="draft", index=True)  # draft, scheduled, live, completed
    access_mode = db.Column(db.String(20), default="open")  # open, invite, password
    exam_password = db.Column(db.String(255))
    max_candidates = db.Column(db.Integer, default=100)
    duration_minutes = db.Column(db.Integer, default=60)
    scheduled_start = db.Column(db.DateTime)
    scheduled_end = db.Column(db.DateTime)
    randomize_questions = db.Column(db.Boolean, default=True)
    randomize_options = db.Column(db.Boolean, default=True)
    case_study_pdf = db.Column(db.String(500))
    ip_restriction = db.Column(db.Text)  # comma separated CIDRs/IPs
    email_restriction_domain = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    anti_cheat = db.relationship("AntiCheatConfig", uselist=False, backref="exam", cascade="all, delete-orphan")
    questions = db.relationship("Question", backref="exam", cascade="all, delete-orphan", order_by="Question.order_index")
    candidates = db.relationship("Candidate", backref="exam", cascade="all, delete-orphan")


class AntiCheatConfig(db.Model):
    __tablename__ = "anti_cheat_configs"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    exam_id = db.Column(db.String(36), db.ForeignKey("exams.id"), unique=True, nullable=False)

    disable_copy = db.Column(db.Boolean, default=True)
    disable_paste = db.Column(db.Boolean, default=True)
    disable_right_click = db.Column(db.Boolean, default=True)
    disable_refresh = db.Column(db.Boolean, default=True)
    disable_printing = db.Column(db.Boolean, default=True)
    disable_drag_drop = db.Column(db.Boolean, default=True)
    disable_text_selection = db.Column(db.Boolean, default=True)
    require_fullscreen = db.Column(db.Boolean, default=True)
    detect_tab_switch = db.Column(db.Boolean, default=True)
    detect_window_blur = db.Column(db.Boolean, default=True)
    detect_fullscreen_exit = db.Column(db.Boolean, default=True)
    detect_multiple_login = db.Column(db.Boolean, default=True)

    max_warnings = db.Column(db.Integer, default=3)
    max_tab_switches = db.Column(db.Integer, default=3)
    max_seconds_outside = db.Column(db.Integer, default=30)
    violation_action = db.Column(db.String(20), default="warning")  # warning, auto_submit, terminate


class Question(db.Model):
    __tablename__ = "questions"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    exam_id = db.Column(db.String(36), db.ForeignKey("exams.id"), nullable=False, index=True)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.Text, nullable=False)
    option_b = db.Column(db.Text, nullable=False)
    option_c = db.Column(db.Text)
    option_d = db.Column(db.Text)
    correct_option = db.Column(db.String(1), nullable=False)  # a/b/c/d
    marks = db.Column(db.Float, default=1.0)
    order_index = db.Column(db.Integer, default=0)


class Candidate(db.Model):
    __tablename__ = "candidates"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    exam_id = db.Column(db.String(36), db.ForeignKey("exams.id"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    access_token = db.Column(db.String(64), unique=True, index=True)
    invited = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default="not_started")  # not_started, in_progress, submitted, terminated, barred
    current_question_index = db.Column(db.Integer, default=0)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    remaining_seconds = db.Column(db.Integer)
    score = db.Column(db.Float)
    warnings_count = db.Column(db.Integer, default=0)
    tab_switch_count = db.Column(db.Integer, default=0)
    blur_count = db.Column(db.Integer, default=0)
    fullscreen_exit_count = db.Column(db.Integer, default=0)
    ip_address = db.Column(db.String(64))
    session_token = db.Column(db.String(64))  # for single-session enforcement
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    answers = db.relationship("Answer", backref="candidate", cascade="all, delete-orphan")
    violations = db.relationship("ViolationLog", backref="candidate", cascade="all, delete-orphan")

    __table_args__ = (db.UniqueConstraint("exam_id", "email", name="uq_exam_email"),)


class Answer(db.Model):
    __tablename__ = "answers"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    candidate_id = db.Column(db.String(36), db.ForeignKey("candidates.id"), nullable=False, index=True)
    question_id = db.Column(db.String(36), db.ForeignKey("questions.id"), nullable=False)
    selected_option = db.Column(db.String(1))
    is_correct = db.Column(db.Boolean)
    answered_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("candidate_id", "question_id", name="uq_candidate_question"),)


class ViolationLog(db.Model):
    __tablename__ = "violation_logs"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    candidate_id = db.Column(db.String(36), db.ForeignKey("candidates.id"), nullable=False, index=True)
    exam_id = db.Column(db.String(36), db.ForeignKey("exams.id"), nullable=False, index=True)
    violation_type = db.Column(db.String(50))  # tab_switch, blur, fullscreen_exit, js_disabled, copy, paste, etc.
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    actor_type = db.Column(db.String(20))  # professor / candidate / system
    actor_id = db.Column(db.String(36))
    action = db.Column(db.String(255))
    ip_address = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
