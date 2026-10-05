import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin


class ReportTemplate(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Modelo de laudo/escala (ex.: CARS, ATA, SNAP-IV), fornecido pela
    psicóloga como dado (schema_json), não fixo no código — ver SPEC.md
    seção 3 para o formato esperado."""

    __tablename__ = "report_templates"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("psychologists.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    version: Mapped[int] = mapped_column(Integer, default=1)
    schema_json: Mapped[dict] = mapped_column(JSON)
    # Modelos de protocolo (rule_type "protocolo") não são apagados, só
    # arquivados: laudos antigos continuam apontando para eles.
    arquivado: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    owner: Mapped["Psychologist"] = relationship(back_populates="templates")
    reports: Mapped[list["Report"]] = relationship(back_populates="template")
