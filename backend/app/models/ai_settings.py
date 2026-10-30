"""Tabela `ai_settings`: provedor, modelo e chave de IA (criptografada) de cada psicóloga."""

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin


class AISettings(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Configuração de IA por psicóloga (provedor/modelo/chave), editável
    pela própria psicóloga dentro do sistema — sem precisar mexer no
    `.env` do servidor. Ver SPEC.md seção 5.

    `api_key` guarda o valor **criptografado** (ver `core/security.py`,
    `encrypt_secret`/`decrypt_secret`) — por isso é `Text`, não uma
    `String` curta: o token criptografado é bem maior que a chave
    original."""

    __tablename__ = "ai_settings"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("psychologists.id"), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100))
    api_key: Mapped[str] = mapped_column(Text)
