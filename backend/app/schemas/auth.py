"""Formatos de cadastro, login, perfil e configuração da capa da psicóloga."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class PsychologistRegister(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class PsychologistLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class FaixaDoNome(BaseModel):
    """Retângulo onde o nome do paciente é escrito na capa, em frações
    (0 a 1) da largura/altura da arte."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    largura: float = Field(gt=0, le=1)
    altura: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def cabe_na_capa(self) -> "FaixaDoNome":
        if self.x + self.largura > 1.0001 or self.y + self.altura > 1.0001:
            raise ValueError("A área do nome precisa ficar dentro da capa.")
        return self


class CapaConfig(BaseModel):
    escreverNome: bool = True
    faixa: FaixaDoNome
    corNome: str = Field(default="#ffffff", pattern=r"^#[0-9a-fA-F]{6}$")


class PsychologistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr
    professional_registration: str | None = None
    bio_profissional: str | None = None
    credenciais_assinatura: str | None = None
    tem_capa_personalizada: bool = False
    capa_config: CapaConfig | None = None


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
