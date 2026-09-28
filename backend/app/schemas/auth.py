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
    bio_profissional: str | None = None
    credenciais_assinatura: str | None = None


class PsychologistProfileUpdate(BaseModel):
    # Usado no bloco de assinatura do PDF completo (ex.: registro no CRP).
    professional_registration: str | None = Field(default=None, max_length=100)
    # Bloco "Sobre A Profissional Responsável" impresso no laudo.
    bio_profissional: str | None = Field(default=None, max_length=4000)
    # Linhas de credencial da assinatura, uma por linha.
    credenciais_assinatura: str | None = Field(default=None, max_length=1000)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
