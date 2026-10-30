import mimetypes
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_psychologist
from app.core.database import get_db
from app.core.uploads import ler_upload
from app.models.patient import Patient
from app.models.patient_photo import PatientPhoto
from app.models.psychologist import Psychologist
from app.models.patient_attachment import PatientAttachment
from app.models.guardian_form_submission import GuardianFormSubmission
from app.models.consolidated_report import ConsolidatedReport
from app.schemas.patient import PatientCreate, PatientOut, PatientPhotoOut, PatientUpdate
from app.services.storage import (
    get_photos_storage,
    get_reports_storage,
    get_form_pdfs_storage,
    get_attachments_storage,
    get_guardian_forms_storage,
)

router = APIRouter(prefix="/api/patients", tags=["patients"])

_EXTENSOES_PERMITIDAS = {".jpg", ".jpeg", ".png", ".webp"}


def get_patient_or_404(patient_id: UUID, db: Session, current: Psychologist) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None or patient.owner_id != current.id:
        # Não revela se o paciente existe e é de outra pessoa (SPEC.md
        # seção 5: um psicólogo não pode acessar pacientes de outro).
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente não encontrado")
    return patient


@router.get("", response_model=list[PatientOut])
def list_patients(
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> list[Patient]:
    return db.query(Patient).filter(Patient.owner_id == current.id).order_by(Patient.name).all()


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    data: PatientCreate,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Patient:
    patient = Patient(owner_id=current.id, **data.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Patient:
    return get_patient_or_404(patient_id, db, current)


@router.put("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: UUID,
    data: PatientUpdate,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Patient:
    patient = get_patient_or_404(patient_id, db, current)
    for field, value in data.model_dump().items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: UUID,
    confirmar_historico: bool = Query(default=False),
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> None:
    patient = get_patient_or_404(patient_id, db, current)
    reports = list(patient.reports)
    if reports and not confirmar_historico:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Confirme a exclusão definitiva do paciente e de todo o histórico.",
        )
    arquivos = [(get_photos_storage(), p.file_path) for p in patient.photos]
    for model, storage in (
        (PatientAttachment, get_attachments_storage()),
        (GuardianFormSubmission, get_guardian_forms_storage()),
        (ConsolidatedReport, get_reports_storage()),
    ):
        for registro in db.query(model).filter(model.patient_id == patient.id).all():
            chave = getattr(registro, "file_path", None) or getattr(registro, "pdf_path", None)
            if chave:
                arquivos.append((storage, chave))
            db.delete(registro)
    # Anexos referenciam relatórios: apague os dependentes primeiro.
    db.flush()
    for report in reports:
        if report.pdf_path:
            arquivos.append((get_reports_storage(), report.pdf_path))
        for arquivo in (report.computed_json or {}).get("arquivos", []):
            if arquivo.get("chave"):
                arquivos.append((get_form_pdfs_storage(), arquivo["chave"]))
        for log in report.change_logs:
            db.delete(log)
        db.flush()
        db.delete(report)
    db.flush()
    db.delete(patient)
    db.flush()
    for storage, chave in arquivos:
        storage.delete(chave)
    db.commit()


@router.post("/{patient_id}/photos", response_model=PatientPhotoOut, status_code=status.HTTP_201_CREATED)
def upload_patient_photo(
    patient_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> PatientPhoto:
    """Foto do paciente, usada na galeria/identificação do PDF completo
    (ver ENTREGAS.md — "PDF completo")."""

    patient = get_patient_or_404(patient_id, db, current)

    extensao = Path(file.filename or "").suffix.lower()
    if extensao not in _EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato de imagem não suportado: '{file.filename}'. Envie JPG, PNG ou WEBP.",
        )

    chave = f"{patient.id}/{uuid.uuid4()}{extensao}"
    get_photos_storage().save(chave, ler_upload(file))

    photo = PatientPhoto(patient_id=patient.id, file_path=chave)
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


@router.get("/{patient_id}/photos", response_model=list[PatientPhotoOut])
def list_patient_photos(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> list[PatientPhoto]:
    patient = get_patient_or_404(patient_id, db, current)
    return patient.photos


@router.get("/{patient_id}/photos/{photo_id}/file")
def download_patient_photo(
    patient_id: UUID,
    photo_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Response:
    photo = _get_patient_photo_or_404(patient_id, photo_id, db, current)
    conteudo = get_photos_storage().read(photo.file_path)
    tipo_mime = mimetypes.guess_type(photo.file_path)[0] or "application/octet-stream"
    return Response(content=conteudo, media_type=tipo_mime)


@router.delete("/{patient_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient_photo(
    patient_id: UUID,
    photo_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> None:
    photo = _get_patient_photo_or_404(patient_id, photo_id, db, current)
    get_photos_storage().delete(photo.file_path)
    db.delete(photo)
    db.commit()


def _get_patient_photo_or_404(patient_id: UUID, photo_id: UUID, db: Session, current: Psychologist) -> PatientPhoto:
    patient = get_patient_or_404(patient_id, db, current)
    photo = db.get(PatientPhoto, photo_id)
    if photo is None or photo.patient_id != patient.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foto não encontrada")
    return photo
