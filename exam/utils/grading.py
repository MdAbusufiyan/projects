from extensions import db
from models.models import Answer, Question, Candidate

def grade_candidate(candidate_id):
    candidate = Candidate.query.get(candidate_id)
    if not candidate:
        return None
    questions = {q.id: q for q in Question.query.filter_by(exam_id=candidate.exam_id).all()}
    answers = Answer.query.filter_by(candidate_id=candidate_id).all()

    total_score = 0.0
    for ans in answers:
        q = questions.get(ans.question_id)
        if not q:
            continue
        correct = (ans.selected_option == q.correct_option)
        ans.is_correct = correct
        if correct:
            total_score += q.marks

    candidate.score = total_score
    db.session.commit()
    return total_score
