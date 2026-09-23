import mimetypes
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_psychologist
from app.core.database import get_db
from app.models.patient import Patient
from app.models.patient_photo import PatientPhoto
from app.models.psychologist import Psychologist
from app.models.report import Report
from app.schemas.patient import PatientCreate, PatientOut, PatientPhotoOut, PatientUpdate
from app.services.storage import get_photos_storage

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
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> None:
    patient = get_patient_or_404(patient_id, db, current)
    tem_laudos = db.query(Report).filter(Report.patient_id == patient.id).first() is not None
    if tem_laudos:
        # Paciente com histórico clínico não pode ser apagado silenciosamente
        # — evita perder laudos por engano (e, sem isso, o banco de dados
        # real recusaria a exclusão de forma bem menos clara para quem usa
        # o sistema).
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este paciente tem protocolos no histórico e por isso não pode ser excluído.",
        )
    db.delete(patient)
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
    get_photos_storage().save(chave, file.file.read())

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


def _get_patient_photo_or_404(
    patient_id: UUID, photo_id: UUID, db: Session, current: Psychologist
) -> PatientPhoto:
    patient = get_patient_or_404(patient_id, db, current)
    photo = db.get(PatientPhoto, photo_id)
    if photo is None or photo.patient_id != patient.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foto não encontrada")
    return photo
