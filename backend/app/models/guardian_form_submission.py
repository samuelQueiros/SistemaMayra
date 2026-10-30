"""Tabela `guardian_form_submissions`: formulários preenchidos pelos responsáveis do paciente."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin


class GuardianFormSubmission(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Registro de um formulário preenchido pelos responsáveis/família do
    paciente (ex.: SNAP-IV respondido pelos pais, questionário de anamnese).

    Ponto 4 da revisão de relatórios — fluxo adotado (opção B, sem link
    público): a psicóloga lança no sistema o que os responsáveis
    preencheram (em papel ou verbalmente), preservando o formulário
    original como anexo (`file_path`) e registrando quem preencheu e
    quando. Só depois de `status == "validado"` esses dados podem ser
    usados como base para lançar respostas no laudo/gráficos — nada aqui
    alimenta `answers_json`/`clinical_sections_json` automaticamente, a
    validação é sempre uma ação manual da psicóloga na tela do paciente."""

    __tablename__ = "guardian_form_submissions"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)

    # Qual instrumento/formulário foi preenchido (texto livre, ex.: "SNAP-IV
    # (Pais)", "Anamnese Familiar", "Questionário Escolar").
    kind: Mapped[str] = mapped_column(String(255))

    # Quem preencheu o formulário original e quando — nunca inferido, sempre
    # informado pela psicóloga ao lançar o registro.
    respondent_name: Mapped[str] = mapped_column(String(255))
    respondent_relation: Mapped[str | None] = mapped_column(String(100), default=None)
    filled_at: Mapped[date] = mapped_column(Date)

    # Anexo do formulário original (foto/scan/PDF), preservado sem edição.
    # Chave lógica no storage `guardian_forms`, igual ao padrão de
    # `PatientPhoto.file_path`/`Report.pdf_path`.
    file_path: Mapped[str | None] = mapped_column(String(500), default=None)

    notes: Mapped[str | None] = mapped_column(Text, default=None)

    # pendente | validado | rejeitado — só "validado" deve ser considerado
    # ao preencher o laudo/gráficos manualmente.
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    validated_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("psychologists.id"), default=None)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("psychologists.id"))

    patient: Mapped["Patient"] = relationship()
