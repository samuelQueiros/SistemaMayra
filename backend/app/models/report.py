import uuid

from sqlalchemy import ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin


class Report(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Laudo gerado para um atendimento. created_at também serve como
    "data do atendimento" no histórico do paciente (ver SPEC.md seção 1)."""

    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_patient_id_created_at", "patient_id", "created_at"),)

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("report_templates.id"), index=True)
    answers_json: Mapped[dict] = mapped_column(JSON)
    computed_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    generated_text: Mapped[str | None] = mapped_column(Text, default=None)
    pdf_path: Mapped[str | None] = mapped_column(String(500), default=None)

    # Permitem à psicóloga corrigir manualmente o que aparece no histórico
    # (ex.: nome do modelo, classificação) sem recalcular o motor de
    # regras. Toda alteração fica registrada em ReportChangeLog.
    template_name_override: Mapped[str | None] = mapped_column(String(255), default=None)
    classification_override: Mapped[str | None] = mapped_column(String(255), default=None)

    # Seções clínicas de texto livre/checklist opcionais para o PDF completo
    # (anamnese, histórico, hipóteses diagnósticas com CID, plano de
    # intervenção etc. — ver ClinicalSections em schemas/report.py). Cada
    # laudo antigo sem isso preenchido continua gerando o PDF exatamente
    # como antes (seções omitidas quando ausentes).
    clinical_sections_json: Mapped[dict | None] = mapped_column(JSON, default=None)

    patient: Mapped["Patient"] = relationship(back_populates="reports")
    template: Mapped["ReportTemplate"] = relationship(back_populates="reports")
    change_logs: Mapped[list["ReportChangeLog"]] = relationship(
        back_populates="report", order_by="ReportChangeLog.created_at.desc()"
    )
