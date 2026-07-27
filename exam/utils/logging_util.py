from extensions import db
from models.models import ActivityLog, ViolationLog

def log_activity(actor_type, actor_id, action, ip_address=None):
    entry = ActivityLog(actor_type=actor_type, actor_id=actor_id, action=action, ip_address=ip_address)
    db.session.add(entry)
    db.session.commit()

def log_violation(candidate_id, exam_id, violation_type, details=""):
    entry = ViolationLog(candidate_id=candidate_id, exam_id=exam_id, violation_type=violation_type, details=details)
    db.session.add(entry)
    db.session.commit()
    return entry
