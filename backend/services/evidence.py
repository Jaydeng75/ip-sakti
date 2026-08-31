import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz
import pytesseract
from docx import Document as DocxDocument
from PIL import Image
from pypdf import PdfReader
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

import models
from config import settings

WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}")
EMBEDDING_DIMENSIONS = 256
CHUNK_CHARACTERS = 1_400
CHUNK_OVERLAP = 220


class EvidenceExtractionError(ValueError):
    pass


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int | None
    text: str
    extraction_method: str = "native"


def _ocr_pdf_page(document: fitz.Document, page_index: int) -> str:
    page = document.load_page(page_index)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    return _clean_text(pytesseract.image_to_string(image, lang="eng"))


def _clean_text(value: str) -> str:
    value = value.replace("\x00", " ")
    value = re.sub(r"[\t\r\f\v]+", " ", value)
    value = re.sub(r" +", " ", value)
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def extract_document(path: Path, media_type: str) -> list[ExtractedPage]:
    if media_type == "text/plain":
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
        pages = [ExtractedPage(None, _clean_text(text), "native")]
    elif media_type == "application/pdf":
        reader = PdfReader(path)
        native_pages = [_clean_text(page.extract_text() or "") for page in reader.pages]
        pages = []
        ocr_document = fitz.open(path) if settings.ocr_enabled else None
        try:
            for index, text in enumerate(native_pages, start=1):
                if len(text) >= 20 or ocr_document is None:
                    pages.append(ExtractedPage(index, text, "native"))
                else:
                    pages.append(ExtractedPage(index, _ocr_pdf_page(ocr_document, index - 1), "ocr"))
        finally:
            if ocr_document is not None:
                ocr_document.close()
    elif media_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        document = DocxDocument(path)
        text = "\n\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
        pages = [ExtractedPage(None, _clean_text(text), "native")]
    else:
        raise EvidenceExtractionError("Unsupported evidence format.")

    if not any(page.text for page in pages):
        if media_type == "application/pdf":
            raise EvidenceExtractionError(
                "No machine-readable text was found. Run OCR on this scanned PDF and upload it again."
            )
        raise EvidenceExtractionError("No machine-readable text was found in this document.")
    return pages


def _section_label(text: str) -> str | None:
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first[:240] if 0 < len(first) <= 240 else None


def chunk_pages(pages: list[ExtractedPage]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for page in pages:
        text = page.text
        start = 0
        while start < len(text):
            end = min(len(text), start + CHUNK_CHARACTERS)
            if end < len(text):
                boundary = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
                if boundary > start + CHUNK_CHARACTERS // 2:
                    end = boundary + 1
            content = text[start:end].strip()
            if content:
                chunks.append(
                    {
                        "page_number": page.page_number,
                        "section": _section_label(content),
                        "content": content,
                        "token_count": len(_tokens(content)),
                        "embedding": embed_text(content),
                    }
                )
            if end >= len(text):
                break
            start = max(start + 1, end - CHUNK_OVERLAP)
    return chunks


def _tokens(text: str) -> list[str]:
    return [match.group(0).lower() for match in WORD_RE.finditer(text)]


def embed_text(text: str) -> list[float]:
    """Deterministic local semantic fingerprint used when no external embedding service is configured."""
    vector = [0.0] * EMBEDDING_DIMENSIONS
    tokens = _tokens(text)
    features = tokens + [f"{left}:{right}" for left, right in zip(tokens, tokens[1:], strict=False)]
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True))


def index_document(db: Session, document: models.UploadedDocument) -> dict[str, Any]:
    path = settings.upload_dir / document.stored_name
    pages = extract_document(path, document.media_type)
    chunks = chunk_pages(pages)
    db.execute(delete(models.EvidenceChunk).where(models.EvidenceChunk.document_id == document.id))
    for index, chunk in enumerate(chunks):
        db.add(
            models.EvidenceChunk(
                document_id=document.id,
                case_id=document.case_id,
                chunk_index=index,
                **chunk,
            )
        )
    db.flush()
    return {
        "status": "indexed",
        "page_count": len(pages),
        "chunk_count": len(chunks),
        "ocr_pages": sum(page.extraction_method == "ocr" for page in pages),
        "ocr_required": False,
    }


def document_status(db: Session, document: models.UploadedDocument) -> dict[str, Any]:
    chunks = list(
        db.scalars(
            select(models.EvidenceChunk).where(models.EvidenceChunk.document_id == document.id)
        )
    )
    pages = {chunk.page_number for chunk in chunks if chunk.page_number is not None}
    return {
        "status": "indexed" if chunks else "not_indexed",
        "page_count": len(pages) or (1 if chunks else 0),
        "chunk_count": len(chunks),
        "ocr_required": False,
    }


def retrieve_case_evidence(
    db: Session, case_id: int, query: str, limit: int = 6, minimum_score: float = 0.08
) -> list[dict[str, Any]]:
    rows = db.execute(
        select(models.EvidenceChunk, models.UploadedDocument)
        .join(models.UploadedDocument, models.EvidenceChunk.document_id == models.UploadedDocument.id)
        .where(models.EvidenceChunk.case_id == case_id)
    ).all()
    if not rows:
        return []

    query_tokens = _tokens(query)
    if not query_tokens:
        return []
    query_counts = Counter(query_tokens)
    query_embedding = embed_text(query)
    scored: list[tuple[float, models.EvidenceChunk, models.UploadedDocument]] = []
    for chunk, document in rows:
        content_tokens = Counter(_tokens(chunk.content))
        lexical = sum(min(count, content_tokens.get(token, 0)) for token, count in query_counts.items())
        lexical /= max(1.0, math.sqrt(len(query_tokens) * max(1, chunk.token_count)))
        semantic = max(0.0, _cosine(query_embedding, chunk.embedding or []))
        score = 0.72 * lexical + 0.28 * semantic
        if score >= minimum_score:
            scored.append((score, chunk, document))

    matches = sorted(scored, key=lambda item: item[0], reverse=True)[:limit]
    return [
        {
            "score": round(score, 4),
            "content": chunk.content,
            "page_number": chunk.page_number,
            "section": chunk.section,
            "chunk_index": chunk.chunk_index,
            "document_id": document.id,
            "filename": document.filename,
            "sha256": document.sha256,
            "media_type": document.media_type,
        }
        for score, chunk, document in matches
    ]


def evidence_citation(case_id: int, match: dict[str, Any]) -> dict[str, Any]:
    page = match.get("page_number")
    locator = f"page {page}" if page else f"chunk {match['chunk_index'] + 1}"
    excerpt = re.sub(r"\s+", " ", match["content"]).strip()[:480]
    return {
        "id": f"document-{match['document_id']}-chunk-{match['chunk_index']}",
        "title": match["filename"],
        "authority": "User-supplied case evidence",
        "jurisdiction": "Case document",
        "effective_date": "Not independently verified",
        "url": (
            f"{settings.public_api_url.rstrip('/')}{settings.api_prefix}/cases/{case_id}"
            f"/documents/{match['document_id']}/content"
        ),
        "support_status": "user-supplied-unverified",
        "excerpt": excerpt,
        "locator": locator,
        "source_type": "case_document",
        "content_sha256": match["sha256"],
        "retrieval_score": match["score"],
    }


def evidence_overview(db: Session, case_id: int) -> dict[str, int]:
    documents = list(
        db.scalars(select(models.UploadedDocument).where(models.UploadedDocument.case_id == case_id))
    )
    chunk_count = len(
        list(db.scalars(select(models.EvidenceChunk.id).where(models.EvidenceChunk.case_id == case_id)))
    )
    indexed_document_ids = set(
        db.scalars(select(models.EvidenceChunk.document_id).where(models.EvidenceChunk.case_id == case_id))
    )
    return {
        "document_count": len(documents),
        "indexed_document_count": len(indexed_document_ids),
        "chunk_count": chunk_count,
    }
