import hashlib
import re
import socket
import struct
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from config import settings

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def scan_for_malware(contents: bytes) -> None:
    if not settings.malware_scan_enabled:
        return
    try:
        with socket.create_connection(
            (settings.clamav_host, settings.clamav_port),
            timeout=settings.clamav_timeout_seconds,
        ) as connection:
            connection.sendall(b"zINSTREAM\0")
            for offset in range(0, len(contents), 64 * 1024):
                chunk = contents[offset : offset + 64 * 1024]
                connection.sendall(struct.pack("!I", len(chunk)) + chunk)
            connection.sendall(struct.pack("!I", 0))
            response = connection.recv(4096).decode("utf-8", errors="replace")
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Evidence malware scanning is temporarily unavailable.",
        ) from None
    if "FOUND" in response:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded document failed malware scanning.",
        )
    if "OK" not in response:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Evidence malware scanning returned an indeterminate result.",
        )


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
    scan_for_malware(contents)
    if media_type == "application/pdf" and not contents.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The file does not have a valid PDF signature.",
        )
    if media_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        try:
            with zipfile.ZipFile(BytesIO(contents)) as archive:
                names = set(archive.namelist())
                expanded_size = sum(item.file_size for item in archive.infolist())
                if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                    raise ValueError("missing DOCX structure")
                if expanded_size > settings.max_upload_bytes * 20:
                    raise ValueError("unsafe compressed expansion")
        except (zipfile.BadZipFile, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The file does not have a safe, valid DOCX structure.",
            ) from None
    if media_type == "text/plain" and b"\x00" in contents[:8192]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The text file appears to contain binary content.",
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
