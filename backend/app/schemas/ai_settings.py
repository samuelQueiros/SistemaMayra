from pydantic import BaseModel, Field, field_validator

from app.services.ai.provedores import PROVEDORES


class AISettingsUpdate(BaseModel):
    provider: str
    model: str = Field(min_length=1, max_length=100)
    api_key: str = Field(min_length=1, max_length=500)

    @field_validator("provider")
    @classmethod
    def provedor_conhecido(cls, valor: str) -> str:
        if valor not in PROVEDORES:
            raise ValueError(f"Provedor de IA desconhecido: '{valor}'.")
        return valor


class AISettingsOut(BaseModel):
    provider: str
    model: str
    api_key_configured: bool
    api_key_preview: str | None = None


class ProvedorOut(BaseModel):
    id: str
    nome: str
    leitura_pdf: str
    modelos: list[str]
    link_chave: str
    observacao: str | None = None
