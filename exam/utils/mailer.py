from flask import current_app
from flask_mail import Message
from extensions import mail

def send_invite_email(to_email, candidate_name, exam_title, exam_link, exam_password=None):
    subject = f"Exam Invitation: {exam_title}"
    body = f"""Hello {candidate_name},

You have been invited to take the exam: {exam_title}

Your unique exam link:
{exam_link}
"""
    if exam_password:
        body += f"\nExam Password: {exam_password}\n"
    body += "\nThis link is unique to you. Do not share it.\n\nGood luck!"

    msg = Message(subject=subject, recipients=[to_email], body=body)
    try:
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Mail send failed for {to_email}: {e}")
        return False
