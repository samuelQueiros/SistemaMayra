"""Formulários preenchidos pelos responsáveis (fluxo manual): a psicóloga lança o registro, guarda o
arquivo original e depois valida ou rejeita. Nada daqui alimenta o laudo sozinho."""

import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_psychologist
from app.api.patients import get_patient_or_404
from app.core.database import get_db
from app.core.uploads import ler_upload
from app.models.guardian_form_submission import GuardianFormSubmission
from app.models.psychologist import Psychologist
from app.schemas.guardian_form_submission import (
    GuardianFormSubmissionCreate,
    GuardianFormSubmissionOut,
)
from app.services.storage import get_guardian_forms_storage

router = APIRouter(prefix="/api/patients/{patient_id}/guardian-forms", tags=["guardian-forms"])

_EXTENSOES_PERMITIDAS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
_STATUS_VALIDOS = {"pendente", "validado", "rejeitado"}


@router.get("", response_model=list[GuardianFormSubmissionOut])
def list_guardian_forms(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> list[GuardianFormSubmission]:
    """Registros do paciente, do mais novo para o mais antigo."""
    patient = get_patient_or_404(patient_id, db, current)
    return (
        db.query(GuardianFormSubmission)
        .filter(GuardianFormSubmission.patient_id == patient.id)
        .order_by(GuardianFormSubmission.filled_at.desc())
        .all()
    )


@router.post("", response_model=GuardianFormSubmissionOut, status_code=status.HTTP_201_CREATED)
def create_guardian_form(
    patient_id: UUID,
    data: GuardianFormSubmissionCreate,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> GuardianFormSubmission:
    """Registra que um responsável preencheu um formulário (SNAP-IV, uma
    anamnese, etc.) fora do sistema — em papel ou verbalmente. Fica com
    status "pendente" até a psicóloga revisar e validar (ver
    `validate_guardian_form`); nenhum dado é lançado automaticamente em
    `answers_json`/`clinical_sections_json` a partir daqui (ponto 4 da
    revisão de relatórios)."""

    patient = get_patient_or_404(patient_id, db, current)
    submission = GuardianFormSubmission(
        patient_id=patient.id,
        created_by_id=current.id,
        **data.model_dump(),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.post(
    "/{submission_id}/file",
    response_model=GuardianFormSubmissionOut,
)
def upload_guardian_form_file(
    patient_id: UUID,
    submission_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> GuardianFormSubmission:
    """Anexa o formulário original (foto/scan/PDF) — preservado sem edição,
    ver `GuardianFormSubmission.file_path`."""

    submission = _get_submission_or_404(patient_id, submission_id, db, current)

    extensao = Path(file.filename or "").suffix.lower()
    if extensao not in _EXTENSOES_PERMITIDAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato de arquivo não suportado: '{file.filename}'. Envie JPG, PNG, WEBP ou PDF.",
        )

    chave = f"{patient_id}/{submission.id}/{uuid.uuid4()}{extensao}"
    get_guardian_forms_storage().save(chave, ler_upload(file))

    submission.file_path = chave
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/{submission_id}/file")
def download_guardian_form_file(
    patient_id: UUID,
    submission_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Response:
    """Devolve o arquivo original anexado ao registro (404 se não há arquivo)."""
    submission = _get_submission_or_404(patient_id, submission_id, db, current)
    if not submission.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Este registro não tem anexo.")
    conteudo = get_guardian_forms_storage().read(submission.file_path)
    tipo_mime = mimetypes.guess_type(submission.file_path)[0] or "application/octet-stream"
    return Response(content=conteudo, media_type=tipo_mime)


@router.post("/{submission_id}/validate", response_model=GuardianFormSubmissionOut)
def validate_guardian_form(
    patient_id: UUID,
    submission_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> GuardianFormSubmission:
    """Marca o registro como "validado" — só depois disso a psicóloga deve
    considerar os dados confiáveis para lançar no laudo/gráficos. Esta rota
    não copia nada automaticamente para `answers_json`; a psicóloga
    continua lançando os valores manualmente no formulário, agora sabendo
    que a fonte já foi conferida."""

    submission = _get_submission_or_404(patient_id, submission_id, db, current)
    submission.status = "validado"
    submission.validated_by_id = current.id
    submission.validated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(submission)
    return submission


@router.post("/{submission_id}/reject", response_model=GuardianFormSubmissionOut)
def reject_guardian_form(
    patient_id: UUID,
    submission_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> GuardianFormSubmission:
    """Marca o registro como `rejeitado`, guardando quem decidiu e quando."""
    submission = _get_submission_or_404(patient_id, submission_id, db, current)
    submission.status = "rejeitado"
    submission.validated_by_id = current.id
    submission.validated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(submission)
    return submission


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_guardian_form(
    patient_id: UUID,
    submission_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> None:
    """Apaga o registro e o arquivo original do storage."""
    submission = _get_submission_or_404(patient_id, submission_id, db, current)
    if submission.file_path:
        get_guardian_forms_storage().delete(submission.file_path)
    db.delete(submission)
    db.commit()


def _get_submission_or_404(
    patient_id: UUID, submission_id: UUID, db: Session, current: Psychologist
) -> GuardianFormSubmission:
    patient = get_patient_or_404(patient_id, db, current)
    submission = db.get(GuardianFormSubmission, submission_id)
    if submission is None or submission.patient_id != patient.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro não encontrado")
    return submission
