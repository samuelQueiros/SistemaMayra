import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin


class PatientPhoto(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Foto do paciente, usada na seção de identificação/galeria do PDF
    completo (ver ENTREGAS.md). Arquivo salvo em
    backend/storage/photos/{patient_id}/{uuid}.{ext}."""

    __tablename__ = "patient_photos"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    file_path: Mapped[str] = mapped_column(String(500))
    caption: Mapped[str | None] = mapped_column(String(255), default=None)

    patient: Mapped["Patient"] = relationship(back_populates="photos")
