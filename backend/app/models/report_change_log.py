import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin


class ReportChangeLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Registro de auditoria: toda edição manual feita num laudo do
    histórico (ex.: corrigir o nome do modelo ou a classificação) fica
    guardada aqui, com quem mudou, quando, e o valor antes/depois."""

    __tablename__ = "report_change_logs"
    __table_args__ = (Index("ix_report_change_logs_created_at", "created_at"),)

    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reports.id"), index=True)
    psychologist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("psychologists.id"), index=True)
    field: Mapped[str] = mapped_column(String(100))
    old_value: Mapped[str | None] = mapped_column(Text, default=None)
    new_value: Mapped[str | None] = mapped_column(Text, default=None)

    report: Mapped["Report"] = relationship(back_populates="change_logs")
    psychologist: Mapped["Psychologist"] = relationship()
