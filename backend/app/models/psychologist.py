from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin


class Psychologist(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "psychologists"

    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # Usado no bloco de assinatura do PDF completo (ex.: registro no CRP).
    professional_registration: Mapped[str | None] = mapped_column(String(100), default=None)
    # Texto do bloco "Sobre A Profissional Responsável" impresso perto do
    # final do laudo, antes da assinatura. Se vazio, o formulário usa um
    # texto padrão (ver `perfilProfissional()` em formulario-novo-paciente.html).
    bio_profissional: Mapped[str | None] = mapped_column(Text, default=None)
    # Linhas de credencial exibidas abaixo do nome na assinatura do laudo,
    # uma por linha (ex.: "Neuropsicopedagoga Clínica"). Se vazio, usa o
    # padrão do formulário.
    credenciais_assinatura: Mapped[str | None] = mapped_column(Text, default=None)

    patients: Mapped[list["Patient"]] = relationship(back_populates="owner")
    templates: Mapped[list["ReportTemplate"]] = relationship(back_populates="owner")
