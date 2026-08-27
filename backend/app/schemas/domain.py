from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.domain import AlertStatus, CaseStatus, Role


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=128)
    workspace_name: str = Field(default="Fraud Operations", min_length=2, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(ORMModel):
    id: str
    workspace_id: str
    email: str
    full_name: str
    role: Role


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class TransactionCreate(BaseModel):
    external_id: str | None = None
    account_id: str
    customer_id: str | None = None
    merchant_id: str
    merchant_name: str
    amount: float = Field(gt=0, le=10_000_000)
    currency: str = Field(default="USD", min_length=3, max_length=8)
    device_id: str
    ip_address: str
    location: str
    occurred_at: datetime | None = None
    status: str = "APPROVED"
    source: str = "API"


class TransactionOut(ORMModel):
    id: str
    external_id: str
    account_id: str
    customer_id: str | None
    merchant_id: str
    merchant_name: str
    amount: float
    currency: str
    device_id: str
    ip_address: str
    location: str
    occurred_at: datetime
    status: str
    source: str
    risk_score: float
    risk_level: str
    created_at: datetime


class AlertOut(ORMModel):
    id: str
    transaction_id: str | None
    title: str
    severity: str
    risk_score: float
    status: AlertStatus
    assigned_to: str | None
    explanation: str
    evidence: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AlertUpdate(BaseModel):
    status: AlertStatus | None = None
    assigned_to: str | None = None


class CaseCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    severity: str = "HIGH"
    alert_ids: list[str] = Field(default_factory=list)
    assigned_to: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class CaseUpdate(BaseModel):
    title: str | None = None
    severity: str | None = None
    status: CaseStatus | None = None
    assigned_to: str | None = None
    decision: str | None = None


class CaseOut(ORMModel):
    id: str
    title: str
    severity: str
    status: CaseStatus
    assigned_to: str | None
    created_by: str
    decision: str | None
    evidence: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class NoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class SimulationRequest(BaseModel):
    speed: int = Field(default=1, ge=1, le=10)


class ModelTrainRequest(BaseModel):
    model_type: str = Field(default="LOGISTIC_REGRESSION", pattern="^(LOGISTIC_REGRESSION|XGBOOST|STATIC_GNN|TEMPORAL_GNN)$")
    samples: int = Field(default=1200, ge=200, le=10000)


class AssistantRequest(BaseModel):
    alert_id: str | None = None
    case_id: str | None = None
    question: str | None = Field(default=None, max_length=1000)
