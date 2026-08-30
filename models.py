from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    Float,
    JSON
)
from sqlalchemy.sql import func

from database import Base




class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)

    created_at = Column(DateTime, server_default=func.now())




class SessionToken(Base):
    __tablename__ = "session_tokens"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    token = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)




class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    jurisdiction = Column(
        String,
        default="India",
        nullable=False
    )

    status = Column(
        String,
        default="active",
        nullable=False
    )

    created_at = Column(DateTime, server_default=func.now())

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )



class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(
        Integer,
        ForeignKey("cases.id"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)

    jurisdiction = Column(
        String,
        default="India",
        nullable=False
    )

    model_used = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=func.now())




class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(
        Integer,
        ForeignKey("cases.id"),
        nullable=False
    )

    filename = Column(String, nullable=False)

    content_type = Column(String, nullable=True)

    file_path = Column(String, nullable=False)

    storage_provider = Column(
        String,
        default="local",
        nullable=False
    )

    created_at = Column(DateTime, server_default=func.now())



class CorpusDocument(Base):
    __tablename__ = "corpus_documents"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    authority = Column(String, nullable=True)

    jurisdiction = Column(
        String,
        default="India",
        nullable=False
    )

    version = Column(String, nullable=True)

    effective_date = Column(String, nullable=True)

    source_url = Column(Text, nullable=True)

    document_type = Column(String, nullable=True)

    namespace = Column(String, nullable=True)

    created_at = Column(DateTime, server_default=func.now())




class InnovationComponent(Base):
    __tablename__ = "innovation_components"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(
        Integer,
        ForeignKey("cases.id"),
        nullable=False
    )

    ingredient = Column(Text, nullable=True)

    process = Column(Text, nullable=True)

    delivery_mechanism = Column(Text, nullable=True)

    claimed_effect = Column(Text, nullable=True)

    brand = Column(String, nullable=True)

    additional_data = Column(JSON, nullable=True)

    created_at = Column(DateTime, server_default=func.now())




class ProductClassification(Base):
    __tablename__ = "product_classifications"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(
        Integer,
        ForeignKey("cases.id"),
        nullable=False
    )

    classification = Column(
        String,
        nullable=False
    )

    confidence = Column(Float, nullable=True)

    reasoning = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())



class Citation(Base):
    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(
        Integer,
        ForeignKey("cases.id"),
        nullable=False
    )

    corpus_document_id = Column(
        Integer,
        ForeignKey("corpus_documents.id"),
        nullable=True
    )

    document_id = Column(
        Integer,
        ForeignKey("documents.id"),
        nullable=True
    )

    section = Column(String, nullable=True)

    page = Column(Integer, nullable=True)

    source_url = Column(Text, nullable=True)

    chunk_id = Column(String, nullable=True)

    quote = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())




class IPAnalysis(Base):
    __tablename__ = "ip_analyses"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(
        Integer,
        ForeignKey("cases.id"),
        nullable=False
    )

    result = Column(Text, nullable=False)

    confidence = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=func.now())



class ABSAnalysis(Base):
    __tablename__ = "abs_analyses"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(
        Integer,
        ForeignKey("cases.id"),
        nullable=False
    )

    result = Column(Text, nullable=False)

    confidence = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=func.now())




class ScientificEvidence(Base):
    __tablename__ = "scientific_evidence"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(
        Integer,
        ForeignKey("cases.id"),
        nullable=False
    )

    result = Column(Text, nullable=False)

    evidence_level = Column(String, nullable=True)

    confidence = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=func.now())


class TKPriorArtAnalysis(Base):
    __tablename__ = "tk_prior_art_analyses"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(
        Integer,
        ForeignKey("cases.id"),
        nullable=False
    )

    result = Column(Text, nullable=False)

    confidence = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=func.now())



class RegulatoryAnalysis(Base):
    __tablename__ = "regulatory_analyses"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(
        Integer,
        ForeignKey("cases.id"),
        nullable=False
    )

    result = Column(Text, nullable=False)

    jurisdiction = Column(
        String,
        default="India",
        nullable=False
    )

    confidence = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=func.now())




class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(
        Integer,
        ForeignKey("cases.id"),
        nullable=False
    )

    title = Column(String, nullable=False)

    status = Column(
        String,
        default="draft",
        nullable=False
    )

    content = Column(Text, nullable=True)

    file_path = Column(String, nullable=True)

    created_at = Column(DateTime, server_default=func.now())




class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    case_id = Column(
        Integer,
        ForeignKey("cases.id"),
        nullable=True
    )

    action = Column(String, nullable=False)

    query = Column(Text, nullable=True)

    retrieved_sources = Column(JSON, nullable=True)

    model_used = Column(String, nullable=True)

    corpus_version = Column(String, nullable=True)

    generated_response = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())