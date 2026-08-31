import hashlib
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

import models
from config import settings


def content_fingerprint(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _latest(db: Session, source_id: str) -> models.SourceSnapshot | None:
    return db.scalar(
        select(models.SourceSnapshot)
        .where(models.SourceSnapshot.source_id == source_id)
        .order_by(desc(models.SourceSnapshot.checked_at))
        .limit(1)
    )


def check_source(db: Session, source: dict[str, Any]) -> models.SourceSnapshot:
    parsed = urlparse(source["url"])
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Only curated HTTPS sources can be monitored")
    previous = _latest(db, source["id"])
    headers = {"User-Agent": "IP-SAKTI-Source-Monitor/1.0"}
    if previous and previous.etag:
        headers["If-None-Match"] = previous.etag
    if previous and previous.last_modified:
        headers["If-Modified-Since"] = previous.last_modified
    checked_at = datetime.now(UTC)
    status = "unavailable"
    digest = previous.content_sha256 if previous else None
    http_status: int | None = None
    response_headers: dict[str, str] = {}
    summary: dict[str, Any] = {}
    try:
        # Do not follow redirects: monitored URLs are curated, and redirect traversal would
        # widen the outbound network target beyond the reviewed registry entry.
        with httpx.Client(timeout=settings.source_monitor_timeout_seconds, follow_redirects=False) as client:
            with client.stream("GET", source["url"], headers=headers) as response:
                http_status = response.status_code
                response_headers = dict(response.headers)
                if response.status_code == 304:
                    status = "unchanged"
                else:
                    response.raise_for_status()
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > settings.source_monitor_max_bytes:
                            raise ValueError("Source exceeds monitoring byte limit")
                    digest = content_fingerprint(bytes(body))
                    if previous and previous.content_sha256 and previous.content_sha256 != digest:
                        status = "changed"
                        summary = {
                            "previous_sha256": previous.content_sha256,
                            "current_sha256": digest,
                            "requires_human_review": True,
                        }
                    else:
                        status = "baseline" if not previous else "unchanged"
    except (httpx.HTTPError, ValueError) as exc:
        summary = {"error": type(exc).__name__, "requires_human_review": True}
    snapshot = models.SourceSnapshot(
        source_id=source["id"],
        url=source["url"],
        content_sha256=digest,
        etag=response_headers.get("etag"),
        last_modified=response_headers.get("last-modified"),
        http_status=http_status,
        status=status,
        change_summary=summary,
        checked_at=checked_at,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def public_snapshot(snapshot: models.SourceSnapshot) -> dict[str, Any]:
    return {
        "id": snapshot.id,
        "source_id": snapshot.source_id,
        "url": snapshot.url,
        "content_sha256": snapshot.content_sha256,
        "etag": snapshot.etag,
        "last_modified": snapshot.last_modified,
        "http_status": snapshot.http_status,
        "status": snapshot.status,
        "change_summary": snapshot.change_summary,
        "checked_at": snapshot.checked_at,
    }
