from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail

db = SQLAlchemy()
# Eventlet 0.36.x cannot run on Python 3.13 because it does not implement
# Python's ``_thread.start_joinable_thread`` API.  The threaded backend works
# with the standard library and ``simple-websocket`` (installed by
# python-engineio), so it is portable across the supported Python versions.
socketio = SocketIO(async_mode="threading", cors_allowed_origins=[])
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per hour"])
bcrypt = Bcrypt()
login_manager = LoginManager()
mail = Mail()
