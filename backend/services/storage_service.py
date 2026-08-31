import hashlib
import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from config import settings

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


async def save_upload(file: UploadFile) -> dict[str, str | int]:
    media_type = file.content_type or "application/octet-stream"
    if media_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF, TXT and DOCX evidence files are accepted.",
        )
    contents = await file.read(settings.max_upload_bytes + 1)
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds upload limit.",
        )
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    if media_type == "application/pdf" and not contents.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The file does not have a valid PDF signature.",
        )
    safe_original = re.sub(r"[^A-Za-z0-9._ -]", "_", Path(file.filename or "evidence").name)[:255]
    stored_name = f"{uuid.uuid4().hex}{ALLOWED_TYPES[media_type]}"
    destination = settings.upload_dir / stored_name
    destination.write_bytes(contents)
    return {
        "filename": safe_original,
        "stored_name": stored_name,
        "media_type": media_type,
        "size_bytes": len(contents),
        "sha256": hashlib.sha256(contents).hexdigest(),
    }
