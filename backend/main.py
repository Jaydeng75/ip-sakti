import logging
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import (
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

import models
from config import settings
from database import Base, SessionLocal, engine, get_db
from schemas import (
    AnalysisResponse,
    AskRequest,
    AskResponse,
    AuditResponse,
    CaseCreate,
    CaseResponse,
    CaseUpdate,
    ExpertReviewCreate,
    ExpertReviewResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from services.intelligence import (
    DISCLAIMER,
    analyze_case,
    answer_question,
    list_sources,
)
from services.storage_service import save_upload
from services.translation import normalize_language, translate_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("ip-sakti")
bearer = HTTPBearer(auto_error=False)


def validate_runtime() -> None:
    if settings.production:
        if settings.secret_key.startswith("change-me") or len(settings.secret_key) < 32:
            raise RuntimeError("A strong IPSAKTI_SECRET_KEY is required in production.")
        if settings.demo_mode:
            raise RuntimeError("IPSAKTI_DEMO_MODE must be false in production.")
        if settings.database_url.startswith("sqlite"):
            logger.warning(
                "SQLite is intended for a single-instance deployment; use PostgreSQL for horizontal scaling."
            )


def bootstrap_admin() -> None:
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        return
    with SessionLocal() as db:
        existing = db.scalar(select(models.User).where(models.User.email == settings.bootstrap_admin_email.lower()))
        if existing:
            return
        db.add(
            models.User(
                email=settings.bootstrap_admin_email.lower(),
                display_name="IP-SAKTI Administrator",
                password_hash=hash_password(settings.bootstrap_admin_password),
                role="admin",
            )
        )
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_runtime()
    Base.metadata.create_all(bind=engine)
    bootstrap_admin()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Authenticated, source-grounded decision-support API for IP-SAKTI innovation cases.",
    lifespan=lifespan,
    docs_url="/docs" if not settings.production else None,
    redoc_url="/redoc" if not settings.production else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:80]
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    logger.exception("Unhandled request error path=%s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


Db = Annotated[Session, Depends(get_db)]


def audit(
    db: Session,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | str | None,
    details: dict | None = None,
) -> None:
    db.add(
        models.AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details or {},
        )
    )


def current_user(
    db: Db,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> models.User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from None
    user = db.get(models.User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive or missing",
        )
    return user


CurrentUser = Annotated[models.User, Depends(current_user)]


def require_case(db: Session, case_id: int, user: models.User) -> models.InnovationCase:
    case = db.get(models.InnovationCase, case_id)
    if not case or (case.owner_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


def latest_analysis(db: Session, case_id: int) -> models.AnalysisRun:
    run = db.scalar(
        select(models.AnalysisRun)
        .where(models.AnalysisRun.case_id == case_id)
        .order_by(desc(models.AnalysisRun.created_at))
        .limit(1)
    )
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run Analyze Innovation first")
    return run


@app.get("/", include_in_schema=False)
def root():
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
        "disclaimer": DISCLAIMER,
    }


@app.get("/health/live", tags=["health"])
def liveness():
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def readiness(db: Db):
    db.execute(select(1))
    return {"status": "ready", "corpus_version": settings.corpus_version}


@app.post(
    f"{settings.api_prefix}/auth/register",
    response_model=TokenResponse,
    status_code=201,
    tags=["auth"],
)
def register(payload: RegisterRequest, db: Db):
    email = payload.email.lower()
    if db.scalar(select(models.User).where(models.User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = models.User(
        email=email,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    audit(db, user.id, "user.registered", "user", user.id)
    db.commit()
    db.refresh(user)
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        user=UserResponse.model_validate(user),
    )


@app.post(f"{settings.api_prefix}/auth/login", response_model=TokenResponse, tags=["auth"])
def login(payload: LoginRequest, db: Db):
    user = db.scalar(select(models.User).where(models.User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")
    audit(db, user.id, "user.login", "user", user.id)
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        user=UserResponse.model_validate(user),
    )


@app.post(f"{settings.api_prefix}/auth/demo", response_model=TokenResponse, tags=["auth"])
def demo_login(db: Db):
    if not settings.demo_mode or settings.production:
        raise HTTPException(status_code=404, detail="Demo mode is disabled")
    email = "demo@ip-sakti.local"
    user = db.scalar(select(models.User).where(models.User.email == email))
    if not user:
        user = models.User(
            email=email,
            display_name="Demo Analyst",
            password_hash=hash_password(uuid.uuid4().hex),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        user=UserResponse.model_validate(user),
    )


@app.get(f"{settings.api_prefix}/auth/me", response_model=UserResponse, tags=["auth"])
def me(user: CurrentUser):
    return user


@app.get(f"{settings.api_prefix}/cases", response_model=list[CaseResponse], tags=["cases"])
def get_cases(db: Db, user: CurrentUser):
    statement = select(models.InnovationCase).order_by(desc(models.InnovationCase.updated_at))
    if user.role != "admin":
        statement = statement.where(models.InnovationCase.owner_id == user.id)
    return list(db.scalars(statement))


@app.post(
    f"{settings.api_prefix}/cases",
    response_model=CaseResponse,
    status_code=201,
    tags=["cases"],
)
def create_case(payload: CaseCreate, db: Db, user: CurrentUser):
    case = models.InnovationCase(owner_id=user.id, **payload.model_dump())
    db.add(case)
    db.flush()
    audit(db, user.id, "case.created", "case", case.id, {"title": case.title})
    db.commit()
    db.refresh(case)
    return case


@app.get(
    f"{settings.api_prefix}/cases/{{case_id}}",
    response_model=CaseResponse,
    tags=["cases"],
)
def get_case(case_id: int, db: Db, user: CurrentUser):
    return require_case(db, case_id, user)


@app.patch(
    f"{settings.api_prefix}/cases/{{case_id}}",
    response_model=CaseResponse,
    tags=["cases"],
)
def update_case(case_id: int, payload: CaseUpdate, db: Db, user: CurrentUser):
    case = require_case(db, case_id, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(case, field, value)
    case.updated_at = datetime.now(UTC)
    audit(
        db,
        user.id,
        "case.updated",
        "case",
        case.id,
        {"fields": list(payload.model_fields_set)},
    )
    db.commit()
    db.refresh(case)
    return case


@app.delete(f"{settings.api_prefix}/cases/{{case_id}}", status_code=204, tags=["cases"])
def delete_case(case_id: int, db: Db, user: CurrentUser):
    case = require_case(db, case_id, user)
    audit(db, user.id, "case.deleted", "case", case.id, {"title": case.title})
    db.delete(case)
    db.commit()
    return Response(status_code=204)


@app.post(
    f"{settings.api_prefix}/cases/{{case_id}}/analyze",
    response_model=AnalysisResponse,
    tags=["intelligence"],
)
def run_analysis(case_id: int, db: Db, user: CurrentUser):
    case = require_case(db, case_id, user)
    result = analyze_case(case)
    run = models.AnalysisRun(case_id=case.id, corpus_version=settings.corpus_version, result=result)
    case.status = "analyzed"
    db.add(run)
    db.flush()
    audit(
        db,
        user.id,
        "analysis.completed",
        "case",
        case.id,
        {"run_id": run.id, "corpus_version": settings.corpus_version},
    )
    db.commit()
    db.refresh(run)
    return AnalysisResponse(
        id=run.id,
        case_id=case.id,
        corpus_version=run.corpus_version,
        created_at=run.created_at,
        result=run.result,
    )


@app.get(
    f"{settings.api_prefix}/cases/{{case_id}}/analysis/latest",
    response_model=AnalysisResponse,
    tags=["intelligence"],
)
def get_latest_analysis(case_id: int, db: Db, user: CurrentUser):
    require_case(db, case_id, user)
    run = latest_analysis(db, case_id)
    return AnalysisResponse(
        id=run.id,
        case_id=case_id,
        corpus_version=run.corpus_version,
        created_at=run.created_at,
        result=run.result,
    )


@app.post(
    f"{settings.api_prefix}/cases/{{case_id}}/ask",
    response_model=AskResponse,
    tags=["intelligence"],
)
async def ask(case_id: int, payload: AskRequest, db: Db, user: CurrentUser):
    case = require_case(db, case_id, user)
    try:
        input_language, _ = normalize_language(payload.input_language)
        response_language, _ = normalize_language(payload.language)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    input_translation = await translate_text(payload.question, input_language, "English")
    if input_translation.status in {"disabled", "unavailable"}:
        result = {
            "answer": (
                "The question could not be translated reliably into English, so IP-SAKTI did not run legal or evidence retrieval. "
                "Retry when IndicTrans2 is available or submit the question in English."
            ),
            "claim_type": "unsupported",
            "confidence": 0.0,
            "citations": [],
            "requires_human_review": True,
            "limitations": [
                DISCLAIMER,
                f"Safe abstention: {input_language}-to-English translation was {input_translation.status}.",
            ],
        }
    else:
        result = answer_question(case, input_translation.text)

    authoritative_answer = result["answer"]
    output_translation = await translate_text(authoritative_answer, "English", response_language)
    if output_translation.status in {"disabled", "unavailable"} and response_language != "English":
        result["limitations"].append(
            f"IndicTrans2 {response_language} output was {output_translation.status}; the authoritative English response is shown."
        )
    result.update(
        {
            "answer": output_translation.text,
            "authoritative_answer": authoritative_answer,
            "input_language": input_language,
            "response_language": response_language,
            "input_translation": input_translation.public(),
            "output_translation": output_translation.public(),
        }
    )
    message = models.ChatMessage(
        case_id=case.id,
        user_id=user.id,
        question=payload.question,
        answer=authoritative_answer,
        claim_type=result["claim_type"],
        confidence=result["confidence"],
        citations=result["citations"],
    )
    db.add(message)
    db.flush()
    audit(
        db,
        user.id,
        "assistant.answered",
        "case",
        case.id,
        {
            "message_id": message.id,
            "claim_type": result["claim_type"],
            "input_language": input_language,
            "response_language": response_language,
            "input_translation": input_translation.status,
            "output_translation": output_translation.status,
        },
    )
    db.commit()
    return result


@app.get(f"{settings.api_prefix}/cases/{{case_id}}/challenge", tags=["intelligence"])
def challenge(case_id: int, db: Db, user: CurrentUser):
    require_case(db, case_id, user)
    return latest_analysis(db, case_id).result["challenges"]


@app.get(f"{settings.api_prefix}/sources", tags=["sources"])
def sources(
    user: CurrentUser,
    jurisdiction: str | None = Query(default=None, max_length=80),
):
    del user
    return {
        "corpus_version": settings.corpus_version,
        "sources": list_sources(jurisdiction),
    }


@app.post(
    f"{settings.api_prefix}/cases/{{case_id}}/documents",
    status_code=201,
    tags=["evidence"],
)
async def upload_document(case_id: int, db: Db, user: CurrentUser, file: Annotated[UploadFile, File()]):
    case = require_case(db, case_id, user)
    stored = await save_upload(file)
    document = models.UploadedDocument(case_id=case.id, **stored)
    db.add(document)
    db.flush()
    audit(
        db,
        user.id,
        "document.uploaded",
        "document",
        document.id,
        {"case_id": case.id, "sha256": document.sha256},
    )
    db.commit()
    db.refresh(document)
    return {
        "id": document.id,
        "case_id": case.id,
        **stored,
        "created_at": document.created_at,
    }


@app.get(f"{settings.api_prefix}/cases/{{case_id}}/documents", tags=["evidence"])
def get_documents(case_id: int, db: Db, user: CurrentUser):
    require_case(db, case_id, user)
    documents = db.scalars(
        select(models.UploadedDocument)
        .where(models.UploadedDocument.case_id == case_id)
        .order_by(desc(models.UploadedDocument.created_at))
    )
    return [
        {
            "id": item.id,
            "filename": item.filename,
            "media_type": item.media_type,
            "size_bytes": item.size_bytes,
            "sha256": item.sha256,
            "created_at": item.created_at,
        }
        for item in documents
    ]


@app.post(
    f"{settings.api_prefix}/cases/{{case_id}}/expert-review",
    response_model=ExpertReviewResponse,
    status_code=201,
    tags=["review"],
)
def request_expert_review(case_id: int, payload: ExpertReviewCreate, db: Db, user: CurrentUser):
    case = require_case(db, case_id, user)
    review = models.ExpertReviewRequest(case_id=case.id, requested_by=user.id, **payload.model_dump())
    case.status = "review_requested"
    db.add(review)
    db.flush()
    audit(
        db,
        user.id,
        "expert_review.requested",
        "expert_review",
        review.id,
        {"case_id": case.id, "type": review.review_type},
    )
    db.commit()
    db.refresh(review)
    return review


@app.get(f"{settings.api_prefix}/cases/{{case_id}}/report", tags=["reports"])
def report(
    case_id: int,
    db: Db,
    user: CurrentUser,
    accept: Annotated[str | None, Header()] = None,
):
    case = require_case(db, case_id, user)
    run = latest_analysis(db, case_id)
    audit(db, user.id, "report.generated", "case", case.id, {"run_id": run.id})
    db.commit()
    report_data = {
        "report_title": f"IP-SAKTI Innovation Intelligence Report — {case.title}",
        "case": CaseResponse.model_validate(case).model_dump(mode="json"),
        "analysis": run.result,
        "generated_at": datetime.now(UTC).isoformat(),
        "disclaimer": DISCLAIMER,
    }
    if accept and "text/markdown" in accept:
        markdown = (
            f"# {report_data['report_title']}\n\n{run.result['executive_summary']}\n\n## Next actions\n\n"
            + "\n".join(f"- {item}" for item in run.result["next_actions"])
            + f"\n\n> {DISCLAIMER}\n"
        )
        return Response(
            markdown,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="ip-sakti-case-{case.id}.md"'},
        )
    return report_data


@app.get(
    f"{settings.api_prefix}/admin/audit",
    response_model=list[AuditResponse],
    tags=["admin"],
)
def audit_log(db: Db, user: CurrentUser, limit: int = Query(default=100, ge=1, le=500)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator role required")
    return list(db.scalars(select(models.AuditLog).order_by(desc(models.AuditLog.created_at)).limit(limit)))
