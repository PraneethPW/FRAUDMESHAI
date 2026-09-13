from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

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
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)
    external_id: str | None = Field(default=None, min_length=1, max_length=80)
    account_id: str = Field(min_length=1, max_length=80)
    customer_id: str | None = Field(default=None, min_length=1, max_length=80)
    merchant_id: str = Field(min_length=1, max_length=80)
    merchant_name: str = Field(min_length=1, max_length=120)
    amount: float = Field(gt=0, le=10_000_000)
    currency: str = Field(default="USD", pattern=r"^[A-Za-z]{3}$")
    device_id: str = Field(min_length=1, max_length=100)
    ip_address: str = Field(min_length=1, max_length=64)
    location: str = Field(min_length=1, max_length=100)
    occurred_at: datetime | None = None
    status: str = Field(default="APPROVED", pattern="^(APPROVED|DECLINED|PENDING)$")
    source: str = Field(default="API", pattern="^(API|CSV|SIMULATION)$")
    is_fraud: bool | None = None

    @field_validator("occurred_at")
    @classmethod
    def utc_timestamp(cls, value):
        if value is None:
            return value
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value):
        return value.upper()


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
    severity: str = Field(default="HIGH", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    alert_ids: list[str] = Field(default_factory=list)
    assigned_to: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=180)
    severity: str | None = Field(default=None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    status: CaseStatus | None = None
    assigned_to: str | None = None
    decision: str | None = Field(default=None, max_length=5000)


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
    dataset: str = Field(default="SYNTHETIC", pattern="^(SYNTHETIC|WORKSPACE)$")


class AssistantRequest(BaseModel):
    alert_id: str | None = None
    case_id: str | None = None
    question: str | None = Field(default=None, max_length=1000)


class LabelRequest(BaseModel):
    is_fraud: bool
    reason: str = Field(min_length=3, max_length=1000)


class WorkspaceUserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=128)
    role: Role = Role.ANALYST


class WorkspaceUserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=10, max_length=128)
