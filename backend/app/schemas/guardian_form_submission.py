"""Formatos da API de formulários dos responsáveis."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GuardianFormSubmissionCreate(BaseModel):
    kind: str = Field(min_length=1, max_length=255)
    respondent_name: str = Field(min_length=1, max_length=255)
    respondent_relation: str | None = Field(default=None, max_length=100)
    filled_at: date
    notes: str | None = None


class GuardianFormSubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    kind: str
    respondent_name: str
    respondent_relation: str | None
    filled_at: date
    file_path: str | None
    notes: str | None
    status: str
    validated_by_id: UUID | None
    validated_at: datetime | None
    created_by_id: UUID
    created_at: datetime
