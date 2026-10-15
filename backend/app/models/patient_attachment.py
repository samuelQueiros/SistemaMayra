import uuid

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin


class PatientAttachment(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Foto ou documento anexado para completar os dados que faltaram num
    laudo (ficha preenchida à mão, caderneta, relatório escolar, laudo
    anterior). A IA lê o arquivo e sugere valores para os campos pendentes
    (`sugestoes_json`); nada vai para o laudo sem a psicóloga confirmar.

    Diferente de `PatientPhoto` (fotos do paciente impressas no laudo).
    Arquivo no storage "anexos" (`file_path` é a chave lógica)."""

    __tablename__ = "patient_attachments"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    report_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reports.id"), index=True, default=None)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("psychologists.id"))
    nome: Mapped[str] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(100))
    file_path: Mapped[str] = mapped_column(String(500))
    # Seção da tela de pendências em que foi anexado (vazio = anexo geral).
    secao: Mapped[str | None] = mapped_column(String(200), default=None)
    # analisando | pronto | erro
    status: Mapped[str] = mapped_column(String(20), default="analisando")
    # [{"campo_id": ..., "valor": ..., "trecho": ...}] — sugestões já
    # validadas contra o catálogo do protocolo.
    sugestoes_json: Mapped[list | None] = mapped_column(JSON, default=None)
    erro: Mapped[str | None] = mapped_column(Text, default=None)

    patient: Mapped["Patient"] = relationship()
