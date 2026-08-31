import logging
from datetime import UTC, datetime

from sqlalchemy import select

import models
from config import settings
from database import SessionLocal
from services.evidence import evidence_overview, index_document, retrieve_case_evidence

logger = logging.getLogger("ip-sakti.jobs")


def run_reindex_job(job_id: int) -> None:
    with SessionLocal() as db:
        job = db.get(models.ReindexJob, job_id)
        if not job:
            return
        job.status = "running"
        job.started_at = datetime.now(UTC)
        db.commit()
        try:
            documents = list(
                db.scalars(select(models.UploadedDocument).where(models.UploadedDocument.case_id == job.case_id))
            )
            indexed = []
            for document in documents:
                indexed.append({"document_id": document.id, **index_document(db, document)})
            case = db.get(models.InnovationCase, job.case_id)
            if case:
                from services.intelligence import analyze_case

                query = " ".join(
                    value
                    for value in [
                        case.title,
                        case.description,
                        case.intended_use,
                        case.biological_sourcing,
                        " ".join(case.ingredients or []),
                    ]
                    if value
                )
                matches = retrieve_case_evidence(db, case.id, query, limit=8, minimum_score=0.03)
                analysis = analyze_case(case, matches, evidence_overview(db, case.id))
                db.add(
                    models.AnalysisRun(
                        case_id=case.id,
                        corpus_version=settings.corpus_version,
                        result=analysis,
                    )
                )
            job.status = "completed"
            job.result = {
                "document_count": len(documents),
                "documents": indexed,
                "embedding_model": job.embedding_model,
                "embedding_revision": job.embedding_revision,
            }
        except Exception as exc:  # background boundary records a safe failure for operators
            logger.exception("reindex failed job_id=%s", job_id)
            db.rollback()
            job = db.get(models.ReindexJob, job_id)
            if not job:
                return
            job.status = "failed"
            job.error = f"{type(exc).__name__}: evidence reindexing failed"
        job.completed_at = datetime.now(UTC)
        db.commit()
