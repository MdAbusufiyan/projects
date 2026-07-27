import os
import uuid
from werkzeug.utils import secure_filename

try:
    import magic
    HAVE_MAGIC = True
except Exception:
    HAVE_MAGIC = False

ALLOWED_PDF_MIME = {"application/pdf"}
ALLOWED_SHEET_MIME = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
    "text/plain",
}

def _ext_ok(filename, allowed_exts):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_exts

def validate_and_save(file_storage, dest_folder, allowed_exts, allowed_mimes, max_bytes):
    if not file_storage or file_storage.filename == "":
        return None, "No file provided"

    filename = secure_filename(file_storage.filename)
    if not _ext_ok(filename, allowed_exts):
        return None, "File extension not allowed"

    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > max_bytes:
        return None, "File exceeds max allowed size"

    if HAVE_MAGIC:
        head = file_storage.stream.read(2048)
        file_storage.stream.seek(0)
        mime = magic.from_buffer(head, mime=True)
        if mime not in allowed_mimes:
            return None, f"Invalid file content type detected: {mime}"

    os.makedirs(dest_folder, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    full_path = os.path.join(dest_folder, unique_name)
    file_storage.save(full_path)
    return full_path, None
