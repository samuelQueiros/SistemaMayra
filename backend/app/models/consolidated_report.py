import uuid

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin


class ConsolidatedReport(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Parecer consolidado (síntese por IA de vários laudos de um mesmo
    paciente — ver `POST /api/patients/{id}/consolidated-pdf`). Antes,
    esse PDF era gerado e baixado na hora sem ficar salvo em lugar
    nenhum; agora fica registrado para poder ser rebaixado depois sem
    precisar gerar tudo de novo (e sem chamar a IA outra vez)."""

    __tablename__ = "consolidated_reports"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("psychologists.id"), index=True)
    report_ids: Mapped[list[str]] = mapped_column(JSON)
    generated_text: Mapped[str] = mapped_column(Text)
    pdf_path: Mapped[str] = mapped_column(String(500))

    patient: Mapped["Patient"] = relationship()
    owner: Mapped["Psychologist"] = relationship()
