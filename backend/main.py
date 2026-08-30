from fastapi import (
    FastAPI,
    Depends,
    UploadFile,
    File,
    HTTPException
)

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.orm import Session

from database import engine, Base, get_db
import models

from schemas import (
    UserCreate,
    UserLogin,
    CaseCreate,
    CaseUpdate,
    ChatCreate,
    AIResponse,
    InnovationComponentCreate,
    ClassificationCreate,
    CorpusDocumentCreate,
    AnalysisCreate,
    ReportCreate
)

from services import rag_services
from services import storage_service

import hashlib
import secrets




app = FastAPI(
    title="Ayurveda AI Backend",
    version="1.0.0"
)

security = HTTPBearer()



Base.metadata.create_all(bind=engine)




def hash_password(password: str) -> str:

    salt = secrets.token_hex(16)

    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        100000
    )

    return salt + "$" + hashed.hex()


def verify_password(password: str, stored_password: str) -> bool:

    try:
        salt, stored_hash = stored_password.split("$")

        hashed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            100000
        )

        return hashed.hex() == stored_hash

    except ValueError:
        return False



def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):

    token = credentials.credentials

    session = db.query(models.SessionToken).filter(
        models.SessionToken.token == token
    ).first()

    if not session:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )

    user = db.query(models.User).filter(
        models.User.id == session.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user


def require_role(*roles):

    def checker(
        current_user=Depends(get_current_user)
    ):

        if current_user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission for this action"
            )

        return current_user

    return checker




def create_audit_log(
    db,
    user_id=None,
    case_id=None,
    action="",
    query=None,
    retrieved_sources=None,
    model_used=None,
    corpus_version=None,
    generated_response=None
):

    log = models.AuditLog(
        user_id=user_id,
        case_id=case_id,
        action=action,
        query=query,
        retrieved_sources=retrieved_sources,
        model_used=model_used,
        corpus_version=corpus_version,
        generated_response=generated_response
    )

    db.add(log)
    db.commit()




@app.get("/")
def home():

    return {
        "message": "Backend yes",
        "status": "running"
    }



@app.post("/users/register")
def register_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):

    existing_user = db.query(models.User).filter(
        models.User.email == user.email
    ).first()

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="User already exists"
        )

    if user.role not in ["user", "expert", "admin"]:

        raise HTTPException(
            status_code=400,
            detail="Invalid role"
        )

    new_user = models.User(
        email=user.email,
        password=hash_password(user.password),
        role=user.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "id": new_user.id,
        "email": new_user.email,
        "role": new_user.role
    }



@app.post("/users/login")
def login_user(
    user: UserLogin,
    db: Session = Depends(get_db)
):

    existing_user = db.query(models.User).filter(
        models.User.email == user.email
    ).first()

    if not existing_user:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        user.password,
        existing_user.password
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = secrets.token_urlsafe(32)

    session = models.SessionToken(
        user_id=existing_user.id,
        token=token
    )

    db.add(session)
    db.commit()

    return {
        "message": "Login successful",
        "token": token,
        "user": {
            "id": existing_user.id,
            "email": existing_user.email,
            "role": existing_user.role
        }
    }




@app.get("/users/me")
def current_user(
    user=Depends(get_current_user)
):

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role
    }



@app.post("/cases")
def create_case(
    case: CaseCreate,
    db: Session = Depends(get_db)
):

    user = db.query(models.User).filter(
        models.User.id == case.user_id
    ).first()

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    new_case = models.Case(
        user_id=case.user_id,
        name=case.name,
        description=case.description,
        jurisdiction=case.jurisdiction
    )

    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    create_audit_log(
        db=db,
        user_id=case.user_id,
        case_id=new_case.id,
        action="case_created"
    )

    return {
        "id": new_case.id,
        "user_id": new_case.user_id,
        "name": new_case.name,
        "description": new_case.description,
        "jurisdiction": new_case.jurisdiction,
        "status": new_case.status
    }


@app.get("/cases")
def get_cases(
    user_id: int = None,
    db: Session = Depends(get_db)
):

    query = db.query(models.Case)

    if user_id is not None:

        query = query.filter(
            models.Case.user_id == user_id
        )

    cases = query.all()

    return [
        {
            "id": case.id,
            "user_id": case.user_id,
            "name": case.name,
            "description": case.description,
            "jurisdiction": case.jurisdiction,
            "status": case.status
        }

        for case in cases
    ]



@app.get("/cases/{case_id}")
def get_case(
    case_id: int,
    db: Session = Depends(get_db)
):

    case = db.query(models.Case).filter(
        models.Case.id == case_id
    ).first()

    if not case:

        raise HTTPException(
            status_code=404,
            detail="Case not found"
        )

    return {
        "id": case.id,
        "user_id": case.user_id,
        "name": case.name,
        "description": case.description,
        "jurisdiction": case.jurisdiction,
        "status": case.status
    }




@app.put("/cases/{case_id}")
def update_case(
    case_id: int,
    case_update: CaseUpdate,
    db: Session = Depends(get_db)
):

    case = db.query(models.Case).filter(
        models.Case.id == case_id
    ).first()

    if not case:

        raise HTTPException(
            status_code=404,
            detail="Case not found"
        )

    if case_update.name is not None:
        case.name = case_update.name

    if case_update.description is not None:
        case.description = case_update.description

    if case_update.jurisdiction is not None:
        case.jurisdiction = case_update.jurisdiction

    if case_update.status is not None:
        case.status = case_update.status

    db.commit()
    db.refresh(case)

    return {
        "message": "Case updated",
        "id": case.id,
        "name": case.name,
        "description": case.description,
        "jurisdiction": case.jurisdiction,
        "status": case.status
    }




@app.get(
    "/ask",
    response_model=AIResponse
)
def ask(
    question: str,
    case_id: int = 1,
    jurisdiction: str = "India",
    db: Session = Depends(get_db)
):

    result = rag_service.query(
        case_id=case_id,
        message=question,
        jurisdiction=jurisdiction
    )

    create_audit_log(
        db=db,
        case_id=case_id,
        action="rag_query",
        query=question,
        retrieved_sources=result.get("citations"),
        model_used="mock-model",
        generated_response=result.get("answer")
    )

    return result




@app.post("/cases/{case_id}/chat")
def create_chat(
    case_id: int,
    chat: ChatCreate,
    db: Session = Depends(get_db)
):

    case = db.query(models.Case).filter(
        models.Case.id == case_id
    ).first()

    if not case:

        raise HTTPException(
            status_code=404,
            detail="Case not found"
        )

    result = rag_service.query(
        case_id=case_id,
        message=chat.question,
        jurisdiction=case.jurisdiction
    )

    new_chat = models.ChatMessage(
        case_id=case_id,
        question=chat.question,
        answer=result["answer"],
        jurisdiction=case.jurisdiction,
        model_used="mock-model",
        confidence=result["confidence"]
    )

    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    create_audit_log(
        db=db,
        case_id=case_id,
        action="chat_query",
        query=chat.question,
        retrieved_sources=result.get("citations"),
        model_used="mock-model",
        generated_response=result.get("answer")
    )

    return {
        "id": new_chat.id,
        "case_id": case_id,
        "question": new_chat.question,
        "answer": new_chat.answer,
        "jurisdiction": new_chat.jurisdiction,
        "confidence": new_chat.confidence,
        "citations": result["citations"],
        "warnings": result["warnings"],
        "classification": result["classification"],
        "needs_expert_review": result["needs_expert_review"]
    }




@app.get("/cases/{case_id}/chat")
def get_chat_history(
    case_id: int,
    db: Session = Depends(get_db)
):

    chats = db.query(
        models.ChatMessage
    ).filter(
        models.ChatMessage.case_id == case_id
    ).order_by(
        models.ChatMessage.created_at
    ).all()

    return [
        {
            "id": chat.id,
            "question": chat.question,
            "answer": chat.answer,
            "jurisdiction": chat.jurisdiction,
            "confidence": chat.confidence,
            "created_at": chat.created_at
        }

        for chat in chats
    ]



@app.post("/cases/{case_id}/documents")
def upload_document(
    case_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    case = db.query(models.Case).filter(
        models.Case.id == case_id
    ).first()

    if not case:

        raise HTTPException(
            status_code=404,
            detail="Case not found"
        )

    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain"
    ]

    if file.content_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOCX and TXT files are currently supported"
        )

    stored = storage_service.save_file(file)

    new_document = models.Document(
        case_id=case_id,
        filename=file.filename,
        content_type=file.content_type,
        file_path=stored["path"],
        storage_provider=stored["provider"]
    )

    db.add(new_document)
    db.commit()
    db.refresh(new_document)

    create_audit_log(
        db=db,
        case_id=case_id,
        action="document_uploaded"
    )

    return {
        "id": new_document.id,
        "case_id": case_id,
        "filename": new_document.filename,
        "content_type": new_document.content_type,
        "storage_provider": new_document.storage_provider,
        "message": "Document uploaded successfully"
    }



@app.get("/cases/{case_id}/documents")
def get_documents(
    case_id: int,
    db: Session = Depends(get_db)
):

    documents = db.query(
        models.Document
    ).filter(
        models.Document.case_id == case_id
    ).all()

    return [
        {
            "id": document.id,
            "filename": document.filename,
            "content_type": document.content_type,
            "storage_provider": document.storage_provider,
            "created_at": document.created_at
        }

        for document in documents
    ]



@app.post("/cases/{case_id}/innovation-components")
def create_innovation_component(
    case_id: int,
    component: InnovationComponentCreate,
    db: Session = Depends(get_db)
):

    case = db.query(models.Case).filter(
        models.Case.id == case_id
    ).first()

    if not case:

        raise HTTPException(
            status_code=404,
            detail="Case not found"
        )

    new_component = models.InnovationComponent(
        case_id=case_id,
        ingredient=component.ingredient,
        process=component.process,
        delivery_mechanism=component.delivery_mechanism,
        claimed_effect=component.claimed_effect,
        brand=component.brand
    )

    db.add(new_component)
    db.commit()
    db.refresh(new_component)

    return {
        "id": new_component.id,
        "case_id": case_id,
        "ingredient": new_component.ingredient,
        "process": new_component.process,
        "delivery_mechanism": new_component.delivery_mechanism,
        "claimed_effect": new_component.claimed_effect,
        "brand": new_component.brand
    }


@app.get("/cases/{case_id}/innovation-components")
def get_innovation_components(
    case_id: int,
    db: Session = Depends(get_db)
):

    components = db.query(
        models.InnovationComponent
    ).filter(
        models.InnovationComponent.case_id == case_id
    ).all()

    return [
        {
            "id": item.id,
            "ingredient": item.ingredient,
            "process": item.process,
            "delivery_mechanism": item.delivery_mechanism,
            "claimed_effect": item.claimed_effect,
            "brand": item.brand
        }

        for item in components
    ]




@app.post("/cases/{case_id}/classification")
def create_classification(
    case_id: int,
    classification: ClassificationCreate,
    db: Session = Depends(get_db)
):

    new_classification = models.ProductClassification(
        case_id=case_id,
        classification=classification.classification,
        confidence=classification.confidence,
        reasoning=classification.reasoning
    )

    db.add(new_classification)
    db.commit()
    db.refresh(new_classification)

    return {
        "id": new_classification.id,
        "case_id": case_id,
        "classification": new_classification.classification,
        "confidence": new_classification.confidence,
        "reasoning": new_classification.reasoning
    }


@app.get("/cases/{case_id}/classification")
def get_classification(
    case_id: int,
    db: Session = Depends(get_db)
):

    result = db.query(
        models.ProductClassification
    ).filter(
        models.ProductClassification.case_id == case_id
    ).order_by(
        models.ProductClassification.created_at.desc()
    ).first()

    if not result:

        return {
            "message": "No classification available"
        }

    return {
        "id": result.id,
        "classification": result.classification,
        "confidence": result.confidence,
        "reasoning": result.reasoning
    }



@app.post("/corpus/documents")
def create_corpus_document(
    document: CorpusDocumentCreate,
    db: Session = Depends(get_db)
):

    new_document = models.CorpusDocument(
        title=document.title,
        authority=document.authority,
        jurisdiction=document.jurisdiction,
        version=document.version,
        effective_date=document.effective_date,
        source_url=document.source_url,
        document_type=document.document_type,
        namespace=document.namespace
    )

    db.add(new_document)
    db.commit()
    db.refresh(new_document)

    return {
        "id": new_document.id,
        "title": new_document.title,
        "authority": new_document.authority,
        "jurisdiction": new_document.jurisdiction,
        "version": new_document.version,
        "effective_date": new_document.effective_date,
        "source_url": new_document.source_url,
        "document_type": new_document.document_type,
        "namespace": new_document.namespace
    }


@app.get("/corpus/documents")
def get_corpus_documents(
    jurisdiction: str = None,
    db: Session = Depends(get_db)
):

    query = db.query(models.CorpusDocument)

    if jurisdiction:

        query = query.filter(
            models.CorpusDocument.jurisdiction == jurisdiction
        )

    documents = query.all()

    return [
        {
            "id": document.id,
            "title": document.title,
            "authority": document.authority,
            "jurisdiction": document.jurisdiction,
            "version": document.version,
            "effective_date": document.effective_date,
            "source_url": document.source_url,
            "document_type": document.document_type,
            "namespace": document.namespace
        }

        for document in documents
    ]



def save_analysis(
    model_class,
    case_id,
    analysis,
    db,
    extra_fields=None
):

    data = {
        "case_id": case_id,
        "result": analysis.result,
        "confidence": analysis.confidence
    }

    if extra_fields:
        data.update(extra_fields)

    new_result = model_class(**data)

    db.add(new_result)
    db.commit()
    db.refresh(new_result)

    return new_result




@app.post("/cases/{case_id}/analyses/ip")
def create_ip_analysis(
    case_id: int,
    analysis: AnalysisCreate,
    db: Session = Depends(get_db)
):

    result = save_analysis(
        models.IPAnalysis,
        case_id,
        analysis,
        db
    )

    return {
        "id": result.id,
        "case_id": case_id,
        "type": "IP",
        "result": result.result,
        "confidence": result.confidence
    }


@app.get("/cases/{case_id}/analyses/ip")
def get_ip_analysis(
    case_id: int,
    db: Session = Depends(get_db)
):

    results = db.query(
        models.IPAnalysis
    ).filter(
        models.IPAnalysis.case_id == case_id
    ).all()

    return results



@app.post("/cases/{case_id}/analyses/abs")
def create_abs_analysis(
    case_id: int,
    analysis: AnalysisCreate,
    db: Session = Depends(get_db)
):

    result = save_analysis(
        models.ABSAnalysis,
        case_id,
        analysis,
        db
    )

    return {
        "id": result.id,
        "case_id": case_id,
        "type": "ABS",
        "result": result.result,
        "confidence": result.confidence
    }


@app.get("/cases/{case_id}/analyses/abs")
def get_abs_analysis(
    case_id: int,
    db: Session = Depends(get_db)
):

    return db.query(
        models.ABSAnalysis
    ).filter(
        models.ABSAnalysis.case_id == case_id
    ).all()




@app.post("/cases/{case_id}/analyses/scientific")
def create_scientific_analysis(
    case_id: int,
    analysis: AnalysisCreate,
    db: Session = Depends(get_db)
):

    result = save_analysis(
        models.ScientificEvidence,
        case_id,
        analysis,
        db,
        {
            "evidence_level": analysis.evidence_level
        }
    )

    return {
        "id": result.id,
        "case_id": case_id,
        "type": "scientific_evidence",
        "result": result.result,
        "evidence_level": result.evidence_level,
        "confidence": result.confidence
    }


@app.get("/cases/{case_id}/analyses/scientific")
def get_scientific_analysis(
    case_id: int,
    db: Session = Depends(get_db)
):

    return db.query(
        models.ScientificEvidence
    ).filter(
        models.ScientificEvidence.case_id == case_id
    ).all()




@app.post("/cases/{case_id}/analyses/tk-prior-art")
def create_tk_analysis(
    case_id: int,
    analysis: AnalysisCreate,
    db: Session = Depends(get_db)
):

    result = save_analysis(
        models.TKPriorArtAnalysis,
        case_id,
        analysis,
        db
    )

    return {
        "id": result.id,
        "case_id": case_id,
        "type": "TK/prior_art",
        "result": result.result,
        "confidence": result.confidence
    }


@app.get("/cases/{case_id}/analyses/tk-prior-art")
def get_tk_analysis(
    case_id: int,
    db: Session = Depends(get_db)
):

    return db.query(
        models.TKPriorArtAnalysis
    ).filter(
        models.TKPriorArtAnalysis.case_id == case_id
    ).all()



@app.post("/cases/{case_id}/analyses/regulatory")
def create_regulatory_analysis(
    case_id: int,
    analysis: AnalysisCreate,
    jurisdiction: str = "India",
    db: Session = Depends(get_db)
):

    result = save_analysis(
        models.RegulatoryAnalysis,
        case_id,
        analysis,
        db,
        {
            "jurisdiction": jurisdiction
        }
    )

    return {
        "id": result.id,
        "case_id": case_id,
        "type": "regulatory",
        "jurisdiction": result.jurisdiction,
        "result": result.result,
        "confidence": result.confidence
    }


@app.get("/cases/{case_id}/analyses/regulatory")
def get_regulatory_analysis(
    case_id: int,
    db: Session = Depends(get_db)
):

    return db.query(
        models.RegulatoryAnalysis
    ).filter(
        models.RegulatoryAnalysis.case_id == case_id
    ).all()




@app.post("/cases/{case_id}/reports")
def create_report(
    case_id: int,
    report: ReportCreate,
    db: Session = Depends(get_db)
):

    new_report = models.Report(
        case_id=case_id,
        title=report.title,
        content=report.content,
        status="draft"
    )

    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return {
        "id": new_report.id,
        "case_id": case_id,
        "title": new_report.title,
        "status": new_report.status,
        "content": new_report.content
    }


@app.get("/cases/{case_id}/reports")
def get_reports(
    case_id: int,
    db: Session = Depends(get_db)
):

    reports = db.query(
        models.Report
    ).filter(
        models.Report.case_id == case_id
    ).all()

    return reports




@app.get("/audit-logs")
def get_audit_logs(
    db: Session = Depends(get_db)
):

    logs = db.query(
        models.AuditLog
    ).order_by(
        models.AuditLog.created_at.desc()
    ).all()

    return logs