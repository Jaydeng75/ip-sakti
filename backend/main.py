import hashlib
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import (
    BackgroundTasks,
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
from starlette.middleware.trustedhost import TrustedHostMiddleware

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
    SourceMonitorRequest,
    TokenResponse,
    UserResponse,
)
from security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from services.evidence import (
    EvidenceExtractionError,
    document_status,
    evidence_overview,
    index_document,
    retrieve_case_evidence,
)
from services.intelligence import (
    DISCLAIMER,
    analyze_case,
    answer_question,
    list_sources,
)
from services.jobs import run_reindex_job
from services.observability import configure_observability
from services.rate_limit import InMemoryRateLimitMiddleware
from services.reasoning import apply_reasoning_layer
from services.reporting import build_pdf_report
from services.retrieval import embedding_identity
from services.source_monitor import check_source, public_snapshot
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
        if settings.registration_enabled:
            raise RuntimeError("IPSAKTI_REGISTRATION_ENABLED must be false in production; use an approved identity flow.")
        if not settings.malware_scan_enabled:
            raise RuntimeError("IPSAKTI_MALWARE_SCAN_ENABLED must be true in production.")
        if settings.translation_enabled and not settings.translation_service_token:
            raise RuntimeError("IPSAKTI_TRANSLATION_SERVICE_TOKEN is required when translation is enabled in production.")
        if settings.database_url.startswith("sqlite"):
            raise RuntimeError("PostgreSQL is required in production.")
        if settings.embedding_provider == "deterministic":
            raise RuntimeError("A neural IPSAKTI_EMBEDDING_PROVIDER is required in production.")
        if settings.embedding_allow_fallback:
            raise RuntimeError("IPSAKTI_EMBEDDING_ALLOW_FALLBACK must be false in production.")
        if settings.embedding_revision.lower() in {"", "main", "latest"} or settings.embedding_revision.startswith(
            "review-and-pin"
        ):
            raise RuntimeError("Pin an approved embedding revision before production.")
        if settings.reranker_provider != "http" or not settings.reranker_url:
            raise RuntimeError("A dedicated neural reranker endpoint is required in production.")
        if settings.reranker_allow_fallback:
            raise RuntimeError("IPSAKTI_RERANKER_ALLOW_FALLBACK must be false in production.")
        if settings.reranker_revision.lower() in {"", "main", "latest"} or settings.reranker_revision.startswith(
            "review-and-pin"
        ):
            raise RuntimeError("Pin an approved reranker revision before production.")
        if not settings.otel_enabled or not settings.otel_exporter_endpoint:
            raise RuntimeError("Production requires OpenTelemetry and an approved OTLP exporter endpoint.")
        if not settings.external_research_enabled:
            raise RuntimeError("IPSAKTI_EXTERNAL_RESEARCH_ENABLED must be true in production.")
        if not settings.ncbi_contact_email:
            raise RuntimeError("IPSAKTI_NCBI_CONTACT_EMAIL is required for production PubMed research.")
        patent_provider = settings.patent_search_provider.lower()
        if patent_provider not in {"auto", "google_bigquery", "epo_ops"}:
            raise RuntimeError("IPSAKTI_PATENT_SEARCH_PROVIDER must be auto, google_bigquery or epo_ops.")
        bigquery_ready = bool(settings.google_cloud_project)
        epo_ready = bool(settings.epo_ops_consumer_key and settings.epo_ops_consumer_secret)
        if patent_provider == "google_bigquery" and not bigquery_ready:
            raise RuntimeError("IPSAKTI_GOOGLE_CLOUD_PROJECT is required for Google BigQuery patent research.")
        if patent_provider == "epo_ops" and not epo_ready:
            raise RuntimeError("EPO OPS consumer credentials are required when the EPO provider is selected.")
        if patent_provider == "auto" and not (bigquery_ready or epo_ready):
            raise RuntimeError("Configure a Google Cloud billing project or EPO OPS credentials for patent research.")
        if bigquery_ready and patent_provider in {"auto", "google_bigquery"}:
            try:
                import google.auth

                google.auth.default(quota_project_id=settings.google_cloud_project)
            except Exception as exc:
                if patent_provider == "google_bigquery" or not epo_ready:
                    raise RuntimeError(
                        "Google Application Default Credentials are required for BigQuery patent research."
                    ) from exc


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


def seed_demo_cases(db: Session, user: models.User) -> None:
    samples = [
        {
            "title": "Controlled-release Ashwagandha Platform",
            "description": "A standardized Withania somnifera root extract delivered through a controlled-release capsule with batch-specific withanolide controls for daily stress-management support.",
            "ingredients": ["Withania somnifera root extract", "plant-based controlled-release capsule"],
            "product_form": "Controlled-release capsule",
            "intended_use": "Daily stress-management support without a disease-treatment claim",
            "target_markets": ["India", "European Union", "United States"],
            "classical_formulation": False,
            "biological_sourcing": "Cultivated Withania sourced from Rajasthan through a documented Indian supplier",
            "metadata_json": {
                "manufacturing_process": "Hydroethanolic extraction, vacuum concentration and controlled-release coating",
                "quantitative_composition": "Withania somnifera root extract 300 mg per capsule",
                "standardization": "5% total withanolides",
                "extraction_ratio": "10:1; 70:30 ethanol:water",
                "dose": "One capsule twice daily for eight weeks",
                "release_profile": "20–35% marker release at 2 h and at least 85% at 12 h",
                "process_parameters": "Extraction at 50–55°C for 4 h; coating weight gain 3.0–3.5%",
                "proposed_claim": "Supports stress resilience in adults after eight weeks without a disease-treatment claim",
                "brand": "SattvaRelease",
            },
        },
        {
            "title": "Neem Wound-care Hydrogel",
            "description": "A neem-derived topical hydrogel with a specified extraction fraction, polymer network and antimicrobial wound-care claim intended for regulated clinical development.",
            "ingredients": ["Azadirachta indica leaf fraction", "medical-grade hydrogel polymer"],
            "product_form": "Topical hydrogel",
            "intended_use": "Adjunct wound-care treatment",
            "target_markets": ["India", "European Union"],
            "classical_formulation": False,
            "biological_sourcing": "Cultivated neem leaves from Karnataka with supplier and harvest records",
            "metadata_json": {"manufacturing_process": "Solvent-controlled fractionation and sterile gel filling", "brand": "NimbaGel"},
        },
        {
            "title": "Classical-inspired Ayurveda Aahara Infusion",
            "description": "A consumer herbal infusion inspired by documented Ayurvedic ingredients, formulated as an Ayurveda Aahara product with non-therapeutic wellbeing claims.",
            "ingredients": ["Ocimum tenuiflorum leaf", "Zingiber officinale rhizome", "Cinnamomum verum bark"],
            "product_form": "Herbal infusion sachet",
            "intended_use": "General wellbeing beverage",
            "target_markets": ["India"],
            "classical_formulation": True,
            "biological_sourcing": "Domestic cultivated resources sourced through three Indian suppliers",
            "metadata_json": {"manufacturing_process": "Low-temperature drying, milling and fixed-ratio blending", "brand": "Prana Infusion"},
        },
        {
            "title": "BrahmiQ Bacopa Oral-Mucosal Spray",
            "description": "A standardized Bacopa monnieri oral-mucosal spray using a phospholipid-based delivery system designed for rapid absorption and controlled dosing for cognitive-support applications.",
            "ingredients": [
                "Bacopa monnieri standardized extract",
                "Phosphatidylcholine",
                "Glycerol",
                "Xylitol",
                "Purified water",
                "Natural mint flavour",
            ],
            "product_form": "Metered-dose oral spray",
            "intended_use": "Supports memory, attention and cognitive performance in healthy adults.",
            "target_markets": ["India", "United Kingdom"],
            "classical_formulation": False,
            "biological_sourcing": "Bacopa monnieri cultivated and sourced through a registered supplier in Kerala, India, with batch, supplier and collection records maintained.",
            "metadata_json": {
                "manufacturing_process": "Standardized Bacopa extract is incorporated into a phospholipid dispersion under controlled shear and pH, followed by filtration and filling into calibrated metered-dose oral spray containers.",
                "quantitative_composition": "Bacopa monnieri extract equivalent to 150 mg per daily dose; phosphatidylcholine 2% w/v; glycerol 5% w/v; xylitol 3% w/v; purified water q.s.",
                "standardization": "Bacopa extract standardized to 50% total bacosides; bacoside A used as the primary analytical marker with HPLC fingerprinting for batch consistency.",
                "extraction_ratio": "Bacopa monnieri aerial-part extract, DER 8:1, hydroethanolic extraction using 60% ethanol followed by concentration and standardization.",
                "dose": "Two metered sprays twice daily, providing approximately 150 mg Bacopa extract per day, for up to 12 weeks.",
                "release_profile": "Target rapid oral-mucosal dispersion with at least 80% active release within 20 minutes in an in-vitro dissolution/release model.",
                "process_parameters": "pH 5.5-6.5; mixing temperature below 35 degrees Celsius; phospholipid incorporation under controlled shear; spray dose volume 0.15 mL plus or minus 10%.",
                "proposed_claim": "Supports memory, attention and cognitive performance in healthy adults when used daily.",
                "classical_reference": "Bacopa monnieri has documented traditional use in Ayurveda for cognitive and memory-related purposes, but this specific metered oral-spray delivery system is not claimed as a classical formulation.",
                "brand": "BrahmiQ",
            },
        },
    ]
    existing_titles = set(
        db.scalars(select(models.InnovationCase.title).where(models.InnovationCase.owner_id == user.id))
    )
    created = 0
    for payload in samples:
        if payload["title"] in existing_titles:
            continue
        case = models.InnovationCase(owner_id=user.id, status="analyzed", **payload)
        db.add(case)
        db.flush()
        result = analyze_case(case)
        db.add(models.AnalysisRun(case_id=case.id, corpus_version=settings.corpus_version, result=result))
        created += 1
    if created:
        audit(db, user.id, "demo.portfolio_seeded", "user", user.id, {"case_count": created})
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
configure_observability(app)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.hosts)
app.add_middleware(
    InMemoryRateLimitMiddleware,
    requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:80]
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    if settings.production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Server-Timing"] = f"app;dur={duration_ms:.1f}"
    logger.info(
        "request method=%s path=%s status=%s duration_ms=%.1f request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    logger.exception("Unhandled request error path=%s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


Db = Annotated[Session, Depends(get_db)]


def audit_timestamp(value: datetime) -> str:
    normalized = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return normalized.isoformat()


def audit(
    db: Session,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | str | None,
    details: dict | None = None,
) -> None:
    created_at = datetime.now(UTC)
    previous = db.scalar(select(models.AuditLog).order_by(desc(models.AuditLog.id)).limit(1))
    previous_hash = ""
    if previous and isinstance(previous.details, dict):
        previous_hash = previous.details.get("_integrity", {}).get("entry_hash", "")
    public_details = details or {}
    canonical = json.dumps(
        {
            "previous_hash": previous_hash,
            "user_id": user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id is not None else None,
            "details": public_details,
            "created_at": audit_timestamp(created_at),
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    db.add(
        models.AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details={
                **public_details,
                "_integrity": {
                    "algorithm": "sha256-chain-v1",
                    "previous_hash": previous_hash,
                    "entry_hash": entry_hash,
                },
            },
            created_at=created_at,
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
        token_id = str(payload["jti"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from None
    if db.scalar(select(models.RevokedToken).where(models.RevokedToken.jti == token_id)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has been signed out",
        )
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


def require_admin(user: models.User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")


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
    identity = embedding_identity()
    return {
        "status": "ready",
        "corpus_version": settings.corpus_version,
        "embedding_provider": identity["provider"],
        "embedding_model": identity["model"],
        "embedding_revision": identity["revision"],
        "reranker_provider": settings.reranker_provider,
        "reranker_model": settings.reranker_model,
    }


@app.post(
    f"{settings.api_prefix}/auth/register",
    response_model=TokenResponse,
    status_code=201,
    tags=["auth"],
)
def register(payload: RegisterRequest, db: Db):
    if not settings.registration_enabled:
        raise HTTPException(status_code=404, detail="Self-registration is disabled")
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
    seed_demo_cases(db, user)
    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        user=UserResponse.model_validate(user),
    )


@app.get(f"{settings.api_prefix}/auth/me", response_model=UserResponse, tags=["auth"])
def me(user: CurrentUser):
    return user


@app.post(f"{settings.api_prefix}/auth/logout", status_code=204, tags=["auth"])
def logout(
    db: Db,
    user: CurrentUser,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
):
    payload = decode_access_token(credentials.credentials)
    token_id = str(payload["jti"])
    if not db.scalar(select(models.RevokedToken).where(models.RevokedToken.jti == token_id)):
        db.add(
            models.RevokedToken(
                jti=token_id,
                user_id=user.id,
                expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            )
        )
    audit(db, user.id, "user.logged_out", "user", user.id)
    db.commit()
    return Response(status_code=204)


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
    stored_files = [settings.upload_dir / document.stored_name for document in case.documents]
    audit(db, user.id, "case.deleted", "case", case.id, {"title": case.title})
    db.delete(case)
    db.commit()
    for path in stored_files:
        path.unlink(missing_ok=True)
    return Response(status_code=204)


@app.post(
    f"{settings.api_prefix}/cases/{{case_id}}/analyze",
    response_model=AnalysisResponse,
    tags=["intelligence"],
)
def run_analysis(case_id: int, db: Db, user: CurrentUser):
    case = require_case(db, case_id, user)
    query = " ".join(
        value
        for value in [
            case.title,
            case.description,
            case.intended_use,
            case.biological_sourcing,
            " ".join(case.ingredients or []),
            " ".join(str(value) for value in (case.metadata_json or {}).values() if value),
        ]
        if value
    )
    evidence_matches = retrieve_case_evidence(db, case.id, query, limit=8, minimum_score=0.03)
    result = analyze_case(case, evidence_matches, evidence_overview(db, case.id))
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
        evidence_matches = retrieve_case_evidence(db, case.id, input_translation.text, limit=5)
        analysis_run = db.scalar(
            select(models.AnalysisRun)
            .where(models.AnalysisRun.case_id == case.id)
            .order_by(desc(models.AnalysisRun.created_at))
            .limit(1)
        )
        analysis_result = analysis_run.result if analysis_run else None
        result = answer_question(
            case,
            input_translation.text,
            evidence_matches,
            analysis_result,
        )
        result = await apply_reasoning_layer(
            case,
            input_translation.text,
            result,
            analysis_result,
        )

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


@app.get(f"{settings.api_prefix}/cases/{{case_id}}/claim-evidence-graph", tags=["intelligence"])
def claim_evidence_graph(case_id: int, db: Db, user: CurrentUser):
    require_case(db, case_id, user)
    return latest_analysis(db, case_id).result["claim_evidence_graph"]


@app.get(f"{settings.api_prefix}/cases/{{case_id}}/design-around", tags=["intelligence"])
def design_around(case_id: int, db: Db, user: CurrentUser):
    require_case(db, case_id, user)
    return latest_analysis(db, case_id).result["design_around"]


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


@app.get(f"{settings.api_prefix}/sources/changes", tags=["sources"])
def source_changes(db: Db, user: CurrentUser):
    del user
    snapshots = db.scalars(select(models.SourceSnapshot).order_by(desc(models.SourceSnapshot.checked_at)).limit(100))
    return {"snapshots": [public_snapshot(snapshot) for snapshot in snapshots]}


@app.post(f"{settings.api_prefix}/admin/sources/monitor", tags=["admin"])
def monitor_sources(payload: SourceMonitorRequest, db: Db, user: CurrentUser):
    require_admin(user)
    selected = [source for source in list_sources(None) if not payload.source_ids or source["id"] in payload.source_ids]
    snapshots = [check_source(db, source) for source in selected]
    audit(db, user.id, "sources.monitored", "source_registry", None, {"source_count": len(snapshots)})
    db.commit()
    return {"snapshots": [public_snapshot(snapshot) for snapshot in snapshots]}


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
    try:
        ingestion = index_document(db, document)
    except EvidenceExtractionError as exc:
        db.rollback()
        (settings.upload_dir / str(stored["stored_name"])).unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        (settings.upload_dir / str(stored["stored_name"])).unlink(missing_ok=True)
        logger.exception("Evidence ingestion failed case_id=%s filename=%s", case.id, stored["filename"])
        raise HTTPException(status_code=422, detail="The document could not be safely extracted and indexed.") from None
    audit(
        db,
        user.id,
        "document.uploaded",
        "document",
        document.id,
        {"case_id": case.id, "sha256": document.sha256, **ingestion},
    )
    db.commit()
    db.refresh(document)
    return {
        "id": document.id,
        "case_id": case.id,
        **stored,
        **ingestion,
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
            **document_status(db, item),
        }
        for item in documents
    ]


@app.post(f"{settings.api_prefix}/cases/{{case_id}}/reindex", status_code=202, tags=["evidence"])
def reindex_case(case_id: int, background_tasks: BackgroundTasks, db: Db, user: CurrentUser):
    case = require_case(db, case_id, user)
    identity = embedding_identity()
    job = models.ReindexJob(
        case_id=case.id,
        requested_by=user.id,
        embedding_model=identity["model"],
        embedding_revision=identity["revision"],
        result={},
    )
    db.add(job)
    db.flush()
    audit(db, user.id, "evidence.reindex_queued", "case", case.id, {"job_id": job.id})
    db.commit()
    background_tasks.add_task(run_reindex_job, job.id)
    return {"id": job.id, "status": job.status, "embedding_model": job.embedding_model, "embedding_revision": job.embedding_revision}


@app.get(f"{settings.api_prefix}/cases/{{case_id}}/reindex-jobs", tags=["evidence"])
def reindex_jobs(case_id: int, db: Db, user: CurrentUser):
    require_case(db, case_id, user)
    jobs = db.scalars(
        select(models.ReindexJob).where(models.ReindexJob.case_id == case_id).order_by(desc(models.ReindexJob.created_at))
    )
    return [
        {
            "id": job.id,
            "status": job.status,
            "embedding_model": job.embedding_model,
            "embedding_revision": job.embedding_revision,
            "result": job.result,
            "error": job.error,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
        }
        for job in jobs
    ]


@app.get(f"{settings.api_prefix}/cases/{{case_id}}/documents/{{document_id}}/content", tags=["evidence"])
def document_content(case_id: int, document_id: int, db: Db, user: CurrentUser):
    require_case(db, case_id, user)
    document = db.get(models.UploadedDocument, document_id)
    if not document or document.case_id != case_id:
        raise HTTPException(status_code=404, detail="Document not found")
    path = settings.upload_dir / document.stored_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Document content is unavailable")
    audit(db, user.id, "document.viewed", "document", document.id, {"case_id": case_id})
    db.commit()
    return Response(
        path.read_bytes(),
        media_type=document.media_type,
        headers={
            "Content-Disposition": f'inline; filename="{document.filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-SHA256": document.sha256,
        },
    )


@app.delete(
    f"{settings.api_prefix}/cases/{{case_id}}/documents/{{document_id}}",
    status_code=204,
    tags=["evidence"],
)
def delete_document(case_id: int, document_id: int, db: Db, user: CurrentUser):
    require_case(db, case_id, user)
    document = db.get(models.UploadedDocument, document_id)
    if not document or document.case_id != case_id:
        raise HTTPException(status_code=404, detail="Document not found")
    path = settings.upload_dir / document.stored_name
    audit(
        db,
        user.id,
        "document.deleted",
        "document",
        document.id,
        {"case_id": case_id, "sha256": document.sha256},
    )
    db.delete(document)
    db.commit()
    path.unlink(missing_ok=True)
    return Response(status_code=204)


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
    format: str | None = Query(default=None, pattern="^(json|markdown|pdf)$"),
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
    if format == "pdf" or (accept and "application/pdf" in accept):
        content = build_pdf_report(case, run, DISCLAIMER)
        return Response(
            content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="ip-sakti-case-{case.id}.pdf"',
                "Cache-Control": "private, no-store",
            },
        )
    if format == "markdown" or (accept and "text/markdown" in accept):
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


@app.get(f"{settings.api_prefix}/cases/{{case_id}}/audit", response_model=list[AuditResponse], tags=["audit"])
def case_audit(case_id: int, db: Db, user: CurrentUser):
    require_case(db, case_id, user)
    return list(
        db.scalars(
            select(models.AuditLog)
            .where(models.AuditLog.entity_id == str(case_id))
            .order_by(models.AuditLog.created_at)
        )
    )


@app.get(f"{settings.api_prefix}/admin/audit/integrity", tags=["admin"])
def audit_integrity(db: Db, user: CurrentUser):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator role required")
    rows = list(db.scalars(select(models.AuditLog).order_by(models.AuditLog.id)))
    previous_hash = ""
    verified = 0
    for row in rows:
        integrity = row.details.get("_integrity", {}) if isinstance(row.details, dict) else {}
        if not integrity:
            continue
        details = {key: value for key, value in row.details.items() if key != "_integrity"}
        canonical = json.dumps(
            {
                "previous_hash": previous_hash,
                "user_id": row.user_id,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "details": details,
                "created_at": audit_timestamp(row.created_at),
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if integrity.get("previous_hash") != previous_hash or integrity.get("entry_hash") != expected:
            return {"status": "failed", "failed_at": row.id, "verified_entries": verified}
        previous_hash = expected
        verified += 1
    return {"status": "verified", "verified_entries": verified, "head_hash": previous_hash}
