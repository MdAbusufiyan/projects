-- PostgreSQL schema for Online Examination Platform
-- Run this manually if you prefer not to use SQLAlchemy's db.create_all()

CREATE TABLE IF NOT EXISTS professors (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_professors_email ON professors(email);

CREATE TABLE IF NOT EXISTS exams (
    id VARCHAR(36) PRIMARY KEY,
    professor_id VARCHAR(36) NOT NULL REFERENCES professors(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'draft',
    access_mode VARCHAR(20) DEFAULT 'open',
    exam_password VARCHAR(255),
    max_candidates INTEGER DEFAULT 100,
    duration_minutes INTEGER DEFAULT 60,
    scheduled_start TIMESTAMP,
    scheduled_end TIMESTAMP,
    randomize_questions BOOLEAN DEFAULT TRUE,
    randomize_options BOOLEAN DEFAULT TRUE,
    case_study_pdf VARCHAR(500),
    ip_restriction TEXT,
    email_restriction_domain VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_exams_professor ON exams(professor_id);
CREATE INDEX IF NOT EXISTS idx_exams_status ON exams(status);

CREATE TABLE IF NOT EXISTS anti_cheat_configs (
    id VARCHAR(36) PRIMARY KEY,
    exam_id VARCHAR(36) UNIQUE NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    disable_copy BOOLEAN DEFAULT TRUE,
    disable_paste BOOLEAN DEFAULT TRUE,
    disable_right_click BOOLEAN DEFAULT TRUE,
    disable_refresh BOOLEAN DEFAULT TRUE,
    disable_printing BOOLEAN DEFAULT TRUE,
    disable_drag_drop BOOLEAN DEFAULT TRUE,
    disable_text_selection BOOLEAN DEFAULT TRUE,
    require_fullscreen BOOLEAN DEFAULT TRUE,
    detect_tab_switch BOOLEAN DEFAULT TRUE,
    detect_window_blur BOOLEAN DEFAULT TRUE,
    detect_fullscreen_exit BOOLEAN DEFAULT TRUE,
    detect_multiple_login BOOLEAN DEFAULT TRUE,
    max_warnings INTEGER DEFAULT 3,
    max_tab_switches INTEGER DEFAULT 3,
    max_seconds_outside INTEGER DEFAULT 30,
    violation_action VARCHAR(20) DEFAULT 'warning'
);

CREATE TABLE IF NOT EXISTS questions (
    id VARCHAR(36) PRIMARY KEY,
    exam_id VARCHAR(36) NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT,
    option_d TEXT,
    correct_option VARCHAR(1) NOT NULL,
    marks FLOAT DEFAULT 1.0,
    order_index INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_questions_exam ON questions(exam_id);

CREATE TABLE IF NOT EXISTS candidates (
    id VARCHAR(36) PRIMARY KEY,
    exam_id VARCHAR(36) NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    access_token VARCHAR(64) UNIQUE,
    invited BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'not_started',
    current_question_index INTEGER DEFAULT 0,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    remaining_seconds INTEGER,
    score FLOAT,
    warnings_count INTEGER DEFAULT 0,
    tab_switch_count INTEGER DEFAULT 0,
    blur_count INTEGER DEFAULT 0,
    fullscreen_exit_count INTEGER DEFAULT 0,
    ip_address VARCHAR(64),
    session_token VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_exam_email UNIQUE (exam_id, email)
);
CREATE INDEX IF NOT EXISTS idx_candidates_exam ON candidates(exam_id);
CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates(email);

CREATE TABLE IF NOT EXISTS answers (
    id VARCHAR(36) PRIMARY KEY,
    candidate_id VARCHAR(36) NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    question_id VARCHAR(36) NOT NULL REFERENCES questions(id),
    selected_option VARCHAR(1),
    is_correct BOOLEAN,
    answered_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_candidate_question UNIQUE (candidate_id, question_id)
);
CREATE INDEX IF NOT EXISTS idx_answers_candidate ON answers(candidate_id);

CREATE TABLE IF NOT EXISTS violation_logs (
    id VARCHAR(36) PRIMARY KEY,
    candidate_id VARCHAR(36) NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    exam_id VARCHAR(36) NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    violation_type VARCHAR(50),
    details TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_violations_candidate ON violation_logs(candidate_id);

CREATE TABLE IF NOT EXISTS activity_logs (
    id VARCHAR(36) PRIMARY KEY,
    actor_type VARCHAR(20),
    actor_id VARCHAR(36),
    action VARCHAR(255),
    ip_address VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW()
);
