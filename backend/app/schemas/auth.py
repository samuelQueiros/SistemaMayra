from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PsychologistRegister(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class PsychologistLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class PsychologistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr
    professional_registration: str | None = None


class PsychologistProfileUpdate(BaseModel):
    # Usado no bloco de assinatura do PDF completo (ex.: registro no CRP).
    professional_registration: str | None = Field(default=None, max_length=100)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
