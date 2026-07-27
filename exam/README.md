# Online Examination Platform

Production-ready online examination system built with Flask, PostgreSQL,
Flask-SocketIO, vanilla JavaScript, PDF.js, and Chart.js. Designed to run
efficiently on constrained hardware.

## Tech Stack

- Backend: Python 3.11+, Flask, Flask-SocketIO (threading), Flask-Login, Flask-Bcrypt, Flask-Mail, Flask-Limiter, Flask-WTF (CSRF)
- Database: SQLite by default for local development; PostgreSQL via `DATABASE_URL` for production
- Frontend: Pure HTML5, CSS3, Vanilla JavaScript (no frameworks)
- PDF rendering: PDF.js
- Charts: Chart.js (professor analytics, optional extension point)
- Realtime: Socket.IO (Flask-SocketIO)

## Folder Structure

```
exam_platform/
├── app.py                  # Application factory & entrypoint
├── wsgi.py                 # Production WSGI/SocketIO entrypoint
├── config.py                # Config from environment variables
├── extensions.py            # Shared Flask extension instances
├── schema.sql                # Raw SQL schema (optional, alternative to ORM create_all)
├── requirements.txt
├── .env.example
├── models/
│   └── models.py            # SQLAlchemy models
├── routes/
│   ├── auth.py               # Professor register/login/logout
│   ├── professor.py          # Exam CRUD, scheduling, monitoring, export
│   └── candidate.py          # Candidate join, exam room, answer/violation APIs
├── sockets/
│   └── events.py             # Flask-SocketIO event handlers
├── utils/
│   ├── security.py           # Validation, IP restriction, decorators
│   ├── files.py               # Secure file upload validation (PDF/Excel only)
│   ├── pdf_parser.py          # MCQ PDF -> question extraction
│   ├── mailer.py               # Invite email sending
│   ├── grading.py              # Auto-grading logic
│   └── logging_util.py         # Activity & violation logging
├── templates/
│   ├── base.html                # JS-required shell, no-JS fallback
│   ├── index.html
│   ├── partials/
│   ├── professor/                # register, login, dashboard, create/edit exam, monitor
│   ├── candidate/                 # join, exam_room (split screen), result, unavailable
│   └── errors/
├── static/
│   ├── css/main.css               # White/blue/gray theme, responsive
│   └── js/
│       ├── js-guard.js             # Confirms JS is active, removes no-JS banner
│       ├── utils.js                 # fetch wrapper, CSRF header, time formatting
│       ├── anti_cheat.js             # All anti-cheat listeners (copy/paste/right-click/fullscreen/tab/blur/print/refresh)
│       ├── exam_engine.js             # Timer, autosave, navigation, PDF.js rendering, JS-integrity heartbeat
│       ├── professor_dashboard.js      # Question/candidate management AJAX
│       ├── monitor.js                   # Socket.IO live dashboard updates
│       └── lib/                          # Place pdf.min.js, pdf.worker.min.js, chart.umd.min.js here (see README_LIBS.txt)
├── uploads/                            # case_studies/, mcq/, invites/ (gitignored, created at runtime)
└── logs/
```

## Database Schema Summary

| Table | Purpose |
|---|---|
| professors | Professor accounts (bcrypt-hashed passwords) |
| exams | Exam metadata, access mode, scheduling, restrictions |
| anti_cheat_configs | Per-exam anti-cheat toggle configuration |
| questions | MCQs per exam (option a-d, correct option, marks) |
| candidates | Per-exam candidate state, live monitoring counters, score |
| answers | Candidate responses per question (autosaved) |
| violation_logs | Every anti-cheat violation event, timestamped |
| activity_logs | General audit trail (logins, exam creation, etc.) |

## Installation

### 1. System prerequisites (Debian/Ubuntu, suitable for ThinkPad L430)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib libmagic1
```

### 2. PostgreSQL setup

PostgreSQL is optional for local development: without `DATABASE_URL`, the app
creates and uses `exam_platform.db` in the project directory. For production,
create a PostgreSQL database and set `DATABASE_URL` as shown below.

```bash
sudo -u postgres psql -c "CREATE USER exam_user WITH PASSWORD 'exam_pass';"
sudo -u postgres psql -c "CREATE DATABASE exam_platform OWNER exam_user;"
```

Optionally apply the raw schema instead of relying on `db.create_all()`:

```bash
psql -U exam_user -d exam_platform -f schema.sql
```

### 3. Python environment

```bash
cd exam_platform
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Environment variables

```bash
cp .env.example .env
# edit .env: SECRET_KEY, DATABASE_URL (optional locally; required for PostgreSQL), MAIL_* settings
```

### 5. Third-party frontend libraries (offline hosting recommended)

```bash
cd static/js/lib
curl -O https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.0.379/pdf.min.js
curl -O https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.0.379/pdf.worker.min.js
curl -O https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js
cd ../../..
```

### 6. Run (development)

```bash
python app.py
```

### 7. Run (production, low-resource tuned)

```bash
gunicorn --worker-class gthread --workers 1 --threads 4 --timeout 120 -b 127.0.0.1:5000 wsgi:app
```

Use a single threaded worker (`-w 1`) because the application does not
support multiple sync workers sharing the same process without a message
queue (e.g. Redis) for pub/sub across workers. On a ThinkPad L430 (dual-core,
limited RAM), a single threaded worker is the most
memory-efficient configuration.

### 8. Cloudflare Tunnel

```bash
cloudflared tunnel login
cloudflared tunnel create exam-platform
cloudflared tunnel route dns exam-platform exams.yourdomain.com
cloudflared tunnel --config /etc/cloudflared/config.yml run exam-platform
```

Example `config.yml`:

```yaml
tunnel: exam-platform
credentials-file: /home/youruser/.cloudflared/<tunnel-id>.json
ingress:
  - hostname: exams.yourdomain.com
    service: http://127.0.0.1:5000
  - service: http_status:404
```

## Performance Notes (Low RAM / Low CPU)

- SQLAlchemy connection pool capped at 5 + 5 overflow with `pool_pre_ping` and `pool_recycle` to avoid stale connections consuming memory.
- A single threaded worker process avoids the overhead of multiple Python interpreters.
- Heartbeat interval is 15s (not per-second) to minimize server round-trips.
- PDF rendering happens client-side via PDF.js; the server only streams the raw PDF bytes.
- No frontend build step, bundlers, or virtual DOM — pure static assets served directly by Flask/Nginx.
- Rate limiting (Flask-Limiter, in-memory) protects against abusive request floods without needing Redis on a single-node deployment.

## Security Features

- CSRF protection via Flask-WTF on all professor-facing forms.
- SQL injection protection via SQLAlchemy parameterized ORM queries exclusively (no raw string SQL).
- Passwords hashed with bcrypt; sessions are HttpOnly, SameSite=Lax, and secure in production.
- File upload validation restricts extension AND (when `python-magic` is available) actual MIME content for PDF/Excel/CSV uploads only, with size limits enforced server-side.
- IP restriction (CIDR or literal) and email-domain restriction enforced per-exam.
- Every anti-cheat violation and professor/candidate action is logged (`violation_logs`, `activity_logs`) for audit and dispute resolution.
- Candidate exam pages render a persistent name/email watermark; screenshot detection is not attempted because browsers cannot reliably detect it — instead the platform relies on fullscreen enforcement, watermarking, and comprehensive violation logging.

## JavaScript-Required Enforcement

- `base.html` ships a `<noscript>` full-page block instructing users to enable JavaScript, and hides all app content until `js-guard.js` confirms JS execution.
- All exam logic (timer, autosave, navigation, anti-cheat) executes exclusively in JavaScript; there is no non-JS fallback path for taking an exam.
- During an active exam, `exam_engine.js` sends a heartbeat every 15 seconds and runs a client-side integrity interval every 5 seconds. Repeated heartbeat failures trigger a `js_disabled` violation report, which the server marks as `barred` and immediately ends the session, logging the incident for the professor.

## Default Anti-Cheat Violation Flow

1. Candidate triggers a monitored event (tab switch, blur, right-click, fullscreen exit, etc.).
2. `anti_cheat.js` calls `/exam/<id>/api/violation`, which increments the relevant counter and logs a `ViolationLog` row.
3. Server checks `max_warnings` / `max_tab_switches` against the exam's `AntiCheatConfig`.
4. If exceeded, the configured `violation_action` (`warning`, `auto_submit`, `terminate`) is applied and broadcast to the professor's live monitor via Socket.IO.
