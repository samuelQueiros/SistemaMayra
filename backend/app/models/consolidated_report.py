"""Tabela `consolidated_reports` (legado, sem uso novo). Ver a classe."""

import uuid

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin


class ConsolidatedReport(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Parecer consolidado: síntese por IA de vários laudos de um mesmo paciente.

    Legado. A rota que gerava este parecer (`/api/patients/{id}/consolidated-pdf`)
    e as telas foram removidas quando o "Laudo por IA" passou a ser o único
    fluxo de criação por PDFs. A tabela continua no banco (há migration
    aplicada e dados salvos) e os registros são apagados junto com o
    paciente (`api/patients.py`). Não crie registros novos aqui."""

    __tablename__ = "consolidated_reports"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("psychologists.id"), index=True)
    report_ids: Mapped[list[str]] = mapped_column(JSON)
    generated_text: Mapped[str] = mapped_column(Text)
    pdf_path: Mapped[str] = mapped_column(String(500))

    patient: Mapped["Patient"] = relationship()
    owner: Mapped["Psychologist"] = relationship()
