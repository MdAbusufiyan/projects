import re
from PyPDF2 import PdfReader

QUESTION_PATTERN = re.compile(r"^(?:Q(?:uestion)?\s*)?(\d+)[\.\):\-]\s*(.+)", re.IGNORECASE)
OPTION_PATTERN = re.compile(r"^([A-D])[\.\)]\s*(.+)", re.IGNORECASE)
ANSWER_PATTERN = re.compile(r"^Answer\s*[:\-]\s*([A-D])", re.IGNORECASE)
ANSWER_KEY_HEADER = re.compile(r"^Answer\s+Key$", re.IGNORECASE)
ANSWER_KEY_PAIR = re.compile(r"^(\d+)\s+([A-D])$", re.IGNORECASE)
PAGE_HEADER = re.compile(r"^(?:Page\s+\d+|.*\|\s*Educational Use)$", re.IGNORECASE)


def extract_pdf_text(filepath):
    """Return readable text for the in-app fallback when a browser cannot embed a PDF."""
    reader = PdfReader(filepath)
    return "\n\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()


def parse_mcq_pdf(filepath):
    reader = PdfReader(filepath)
    text = ""
    for page in reader.pages:
        text += (page.extract_text() or "") + "\n"

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    questions = []
    current = None
    answer_key_mode = False
    pending_answer_number = None
    answer_key = {}

    for line in lines:
        if PAGE_HEADER.match(line):
            continue
        if ANSWER_KEY_HEADER.match(line):
            answer_key_mode = True
            continue
        if answer_key_mode:
            pair = ANSWER_KEY_PAIR.match(line)
            if pair:
                answer_key[pair.group(1)] = pair.group(2).lower()
                pending_answer_number = None
            elif line.isdigit():
                pending_answer_number = line
            elif pending_answer_number and re.fullmatch(r"[A-D]", line, re.IGNORECASE):
                answer_key[pending_answer_number] = line.lower()
                pending_answer_number = None
            continue

        qm = QUESTION_PATTERN.match(line)
        om = OPTION_PATTERN.match(line)
        am = ANSWER_PATTERN.match(line)

        if qm:
            if current and current.get("question_text"):
                questions.append(current)
            current = {
                "number": qm.group(1), "question_text": qm.group(2),
                "options": {}, "correct_option": None,
            }
        elif om and current is not None:
            current["options"][om.group(1).lower()] = om.group(2)
        elif am and current is not None:
            current["correct_option"] = am.group(1).lower()
        elif current is not None:
            current["question_text"] += " " + line

    if current and current.get("question_text"):
        questions.append(current)

    parsed = []
    for q in questions:
        opts = q["options"]
        correct_option = q.get("correct_option") or answer_key.get(q.get("number"))
        if "a" in opts and "b" in opts and correct_option:
            parsed.append({
                "question_text": q["question_text"],
                "option_a": opts.get("a", ""),
                "option_b": opts.get("b", ""),
                "option_c": opts.get("c", ""),
                "option_d": opts.get("d", ""),
                "correct_option": correct_option,
            })
    return parsed
