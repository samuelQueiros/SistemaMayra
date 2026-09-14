import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin


class Patient(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "patients"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("psychologists.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    birth_date: Mapped[date] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    # Usados na seção "Identificação" do PDF completo (ver ENTREGAS.md).
    sex: Mapped[str | None] = mapped_column(String(20), default=None)
    school_info: Mapped[str | None] = mapped_column(Text, default=None)

    owner: Mapped["Psychologist"] = relationship(back_populates="patients")
    reports: Mapped[list["Report"]] = relationship(back_populates="patient")
    photos: Mapped[list["PatientPhoto"]] = relationship(
        back_populates="patient", order_by="PatientPhoto.created_at", cascade="all, delete-orphan"
    )
