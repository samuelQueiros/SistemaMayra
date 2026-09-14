from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PatientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    birth_date: date
    notes: str | None = None
    sex: str | None = None
    school_info: str | None = None


class PatientUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    birth_date: date
    notes: str | None = None
    sex: str | None = None
    school_info: str | None = None


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    birth_date: date
    notes: str | None = None
    sex: str | None = None
    school_info: str | None = None


class PatientPhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_path: str
    caption: str | None = None
    created_at: datetime
