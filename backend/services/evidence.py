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
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

import models
from config import settings
from services.retrieval import (
    embedding_client,
    embedding_identity,
    passes_evidence_gate,
    reranker_client,
)
from services.retrieval import tokens as retrieval_tokens

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
                    }
                )
            if end >= len(text):
                break
            start = max(start + 1, end - CHUNK_OVERLAP)
    batch = embedding_client().documents([chunk["content"] for chunk in chunks])
    for chunk, vector in zip(chunks, batch.vectors, strict=True):
        chunk.update(
            {
                "embedding": vector,
                "embedding_vector": vector,
                "embedding_provider": batch.provider,
                "embedding_model": batch.model,
                "embedding_revision": batch.revision,
            }
        )
    return chunks


def _tokens(text: str) -> list[str]:
    return retrieval_tokens(text)


def embed_text(text: str) -> list[float]:
    """Compatibility helper; production indexing uses the configured batch embedding provider."""
    return embedding_client().query(text).vectors[0]


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
    embedding = chunks[0] if chunks else {}
    return {
        "status": "indexed",
        "page_count": len(pages),
        "chunk_count": len(chunks),
        "ocr_pages": sum(page.extraction_method == "ocr" for page in pages),
        "ocr_required": False,
        "embedding_provider": embedding.get("embedding_provider"),
        "embedding_model": embedding.get("embedding_model"),
        "embedding_revision": embedding.get("embedding_revision"),
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
        "embedding_provider": chunks[0].embedding_provider if chunks else None,
        "embedding_model": chunks[0].embedding_model if chunks else None,
        "embedding_revision": chunks[0].embedding_revision if chunks else None,
    }


def retrieve_case_evidence(
    db: Session, case_id: int, query: str, limit: int = 6, minimum_score: float = 0.08
) -> list[dict[str, Any]]:
    query_tokens = _tokens(query)
    if not query_tokens:
        return []
    prefetch_limit = max(limit, settings.retrieval_prefetch_limit)
    query_batch = embedding_client().query(query)
    query_embedding = query_batch.vectors[0]
    base_query = (
        select(models.EvidenceChunk, models.UploadedDocument)
        .join(models.UploadedDocument, models.EvidenceChunk.document_id == models.UploadedDocument.id)
        .where(models.EvidenceChunk.case_id == case_id)
    )
    if db.bind and db.bind.dialect.name == "postgresql" and query_batch.provider != "deterministic-fallback":
        semantic_rows = db.execute(
            base_query.where(models.EvidenceChunk.embedding_vector.is_not(None))
            .order_by(models.EvidenceChunk.embedding_vector.cosine_distance(query_embedding))
            .limit(prefetch_limit)
        ).all()
        search_query = func.plainto_tsquery("simple", query)
        lexical_rows = db.execute(
            base_query.order_by(
                func.ts_rank_cd(func.to_tsvector("simple", models.EvidenceChunk.content), search_query).desc()
            ).limit(prefetch_limit)
        ).all()
        rows_by_id = {chunk.id: (chunk, document) for chunk, document in [*semantic_rows, *lexical_rows]}
        rows = list(rows_by_id.values())
    else:
        rows = db.execute(base_query).all()
    if not rows:
        return []

    query_counts = Counter(query_tokens)
    prefetched: list[dict[str, Any]] = []
    for chunk, document in rows:
        content_tokens = Counter(_tokens(chunk.content))
        lexical = sum(min(count, content_tokens.get(token, 0)) for token, count in query_counts.items())
        lexical /= max(1.0, math.sqrt(len(query_tokens) * max(1, chunk.token_count)))
        stored_embedding = (
            chunk.embedding_vector
            if chunk.embedding_vector is not None
            else (chunk.embedding or [])
        )
        semantic = max(0.0, _cosine(query_embedding, stored_embedding))
        hybrid = settings.retrieval_lexical_weight * lexical + settings.retrieval_semantic_weight * semantic
        prefetched.append(
            {
                "hybrid_score": hybrid,
                "lexical_score": lexical,
                "semantic_score": semantic,
                "chunk": chunk,
                "document": document,
            }
        )
    prefetched.sort(key=lambda item: item["hybrid_score"], reverse=True)
    prefetched = prefetched[:prefetch_limit]
    rerank_scores, reranker = reranker_client().score(
        query, [item["chunk"].content for item in prefetched]
    )
    for rank, (item, rerank_score) in enumerate(zip(prefetched, rerank_scores, strict=True), start=1):
        item["prefetch_rank"] = rank
        item["rerank_score"] = rerank_score
        item["score"] = 0.45 * item["hybrid_score"] + 0.55 * rerank_score
    matches = [
        item
        for item in sorted(prefetched, key=lambda candidate: candidate["score"], reverse=True)
        if passes_evidence_gate(
            lexical_score=item["lexical_score"],
            rerank_score=item["rerank_score"],
            combined_score=item["score"],
            minimum_score=minimum_score,
        )
    ][:limit]
    return [
        {
            "score": round(item["score"], 4),
            "lexical_score": round(item["lexical_score"], 4),
            "semantic_score": round(item["semantic_score"], 4),
            "rerank_score": round(item["rerank_score"], 4),
            "prefetch_rank": item["prefetch_rank"],
            "embedding_provider": query_batch.provider,
            "embedding_model": query_batch.model,
            "embedding_revision": query_batch.revision,
            "reranker": reranker,
            "content": item["chunk"].content,
            "page_number": item["chunk"].page_number,
            "section": item["chunk"].section,
            "chunk_index": item["chunk"].chunk_index,
            "document_id": item["document"].id,
            "filename": item["document"].filename,
            "sha256": item["document"].sha256,
            "media_type": item["document"].media_type,
        }
        for item in matches
    ]


def retrieval_status(matches: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    first = (matches or [{}])[0]
    identity = embedding_identity()
    return {
        "method": "hybrid lexical + dense retrieval with candidate prefetch and reranking",
        "prefetch_limit": settings.retrieval_prefetch_limit,
        "embedding_provider": first.get("embedding_provider", identity["provider"]),
        "embedding_model": first.get("embedding_model", identity["model"]),
        "embedding_revision": first.get("embedding_revision", identity["revision"]),
        "reranker": first.get("reranker", settings.reranker_model if settings.reranker_provider == "http" else "heuristic-coverage-v1"),
    }


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
        "lexical_score": match.get("lexical_score"),
        "semantic_score": match.get("semantic_score"),
        "rerank_score": match.get("rerank_score"),
        "prefetch_rank": match.get("prefetch_rank"),
        "embedding_model": match.get("embedding_model"),
        "reranker": match.get("reranker"),
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
