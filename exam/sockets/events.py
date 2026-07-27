from flask_socketio import join_room, leave_room, emit
from flask_login import current_user
from extensions import socketio
from models.models import Exam


def register_socket_events():

    @socketio.on("join_monitor")
    def handle_join_monitor(data):
        exam_id = data.get("exam_id")
        if not exam_id:
            return
        exam = Exam.query.get(exam_id)
        if not exam:
            return
        if not current_user.is_authenticated or exam.professor_id != current_user.id.replace("prof:", "") and exam.professor_id != getattr(current_user, "id", None):
            pass
        join_room(f"monitor_{exam_id}")
        emit("joined", {"exam_id": exam_id})

    @socketio.on("leave_monitor")
    def handle_leave_monitor(data):
        exam_id = data.get("exam_id")
        if exam_id:
            leave_room(f"monitor_{exam_id}")

    @socketio.on("disconnect")
    def handle_disconnect():
        pass
