from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    display_name: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class CaseCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=20, max_length=20_000)
    ingredients: list[str] = Field(default_factory=list, max_length=100)
    product_form: str | None = Field(default=None, max_length=100)
    intended_use: str | None = Field(default=None, max_length=4_000)
    target_markets: list[str] = Field(default_factory=lambda: ["India"], max_length=20)
    classical_formulation: bool = False
    biological_sourcing: str | None = Field(default=None, max_length=4_000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("ingredients", "target_markets")
    @classmethod
    def clean_list(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=180)
    description: str | None = Field(default=None, min_length=20, max_length=20_000)
    status: Literal["draft", "analyzed", "review_requested", "archived"] | None = None
    ingredients: list[str] | None = Field(default=None, max_length=100)
    product_form: str | None = Field(default=None, max_length=100)
    intended_use: str | None = Field(default=None, max_length=4_000)
    target_markets: list[str] | None = Field(default=None, max_length=20)
    classical_formulation: bool | None = None
    biological_sourcing: str | None = Field(default=None, max_length=4_000)
    metadata_json: dict[str, Any] | None = None


class CaseResponse(CaseCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: int
    status: str
    created_at: datetime
    updated_at: datetime


class AnalysisResponse(BaseModel):
    id: int
    case_id: int
    corpus_version: str
    created_at: datetime
    result: dict[str, Any]


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4_000)
    input_language: str = Field(default="English", max_length=40)
    language: str = Field(default="English", max_length=40)


class Citation(BaseModel):
    id: str
    title: str
    authority: str
    jurisdiction: str
    effective_date: str
    url: str
    support_status: str
    excerpt: str


class TranslationInfo(BaseModel):
    provider: Literal["IndicTrans2", "none"]
    status: Literal["identity", "translated", "disabled", "unavailable"]
    source_language: str
    target_language: str
    model: str | None = None
    machine_translated: bool = False


class AskResponse(BaseModel):
    answer: str
    authoritative_answer: str
    input_language: str
    response_language: str
    input_translation: TranslationInfo
    output_translation: TranslationInfo
    claim_type: Literal["legal_fact", "interpretation", "inference", "unsupported"]
    confidence: float = Field(ge=0, le=1)
    citations: list[Citation]
    requires_human_review: bool
    limitations: list[str]


class ExpertReviewCreate(BaseModel):
    review_type: Literal["patent", "regulatory", "abs", "scientific", "full"] = "full"
    notes: str | None = Field(default=None, max_length=2_000)


class ExpertReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    case_id: int
    requested_by: int
    review_type: str
    notes: str | None
    status: str
    created_at: datetime


class AuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int | None
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, Any]
    created_at: datetime
