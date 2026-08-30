from pydantic import BaseModel
from typing import Optional, List




class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "user"


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    role: str



class CaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    jurisdiction: str = "India"
    user_id: int


class CaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    jurisdiction: Optional[str] = None
    status: Optional[str] = None



class ChatCreate(BaseModel):
    question: str




class CitationResponse(BaseModel):
    document_id: Optional[int] = None
    corpus_document_id: Optional[int] = None
    section: Optional[str] = None
    page: Optional[int] = None
    source_url: Optional[str] = None
    chunk_id: Optional[str] = None




class AIResponse(BaseModel):
    answer: str
    jurisdiction: str
    confidence: float
    citations: List[CitationResponse]
    warnings: List[str]
    classification: Optional[str] = None
    needs_expert_review: bool




class InnovationComponentCreate(BaseModel):
    ingredient: Optional[str] = None
    process: Optional[str] = None
    delivery_mechanism: Optional[str] = None
    claimed_effect: Optional[str] = None
    brand: Optional[str] = None




class ClassificationCreate(BaseModel):
    classification: str
    confidence: Optional[float] = None
    reasoning: Optional[str] = None



class CorpusDocumentCreate(BaseModel):
    title: str
    authority: Optional[str] = None
    jurisdiction: str = "India"
    version: Optional[str] = None
    effective_date: Optional[str] = None
    source_url: Optional[str] = None
    document_type: Optional[str] = None
    namespace: Optional[str] = None



class AnalysisCreate(BaseModel):
    result: str
    confidence: Optional[float] = None
    evidence_level: Optional[str] = None



class ReportCreate(BaseModel):
    title: str
    content: Optional[str] = None