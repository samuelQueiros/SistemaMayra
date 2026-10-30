"""Modelos de protocolo configuráveis (Configurações → "Modelos De
Protocolo"). Cada modelo é um `ReportTemplate` com `rule_type: "protocolo"`
— ver `app/schemas/protocolo.py`. O protocolo fixo
(formulario-novo-paciente.html) não passa por aqui."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_psychologist
from app.core.database import get_db
from app.models.psychologist import Psychologist
from app.models.report_template import ReportTemplate
from app.schemas.protocolo import ProtocoloIn, ProtocoloOut

router = APIRouter(prefix="/api/protocolos", tags=["protocolos"])

RULE_TYPE = "protocolo"


def _get_protocolo_or_404(protocolo_id: UUID, db: Session, current: Psychologist) -> ReportTemplate:
    modelo = db.get(ReportTemplate, protocolo_id)
    if modelo is None or modelo.owner_id != current.id or modelo.schema_json.get("rule_type") != RULE_TYPE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo de protocolo não encontrado")
    return modelo


@router.get("", response_model=list[ProtocoloOut])
def list_protocolos(
    incluir_arquivados: bool = False,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> list[ReportTemplate]:
    """Modelos de protocolo da psicóloga (ativos e arquivados)."""
    modelos = db.query(ReportTemplate).filter(ReportTemplate.owner_id == current.id).order_by(ReportTemplate.name).all()
    return [
        m for m in modelos if m.schema_json.get("rule_type") == RULE_TYPE and (incluir_arquivados or not m.arquivado)
    ]


@router.post("", response_model=ProtocoloOut, status_code=status.HTTP_201_CREATED)
def create_protocolo(
    data: ProtocoloIn,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> ReportTemplate:
    """Cria um modelo de protocolo próprio (`rule_type: "protocolo"`, formato de `schemas/protocolo.py`)."""
    schema = data.schema_json.model_dump(mode="json")
    modelo = ReportTemplate(owner_id=current.id, name=schema["name"], version=1, schema_json=schema)
    db.add(modelo)
    db.commit()
    db.refresh(modelo)
    return modelo


@router.get("/{protocolo_id}", response_model=ProtocoloOut)
def get_protocolo(
    protocolo_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> ReportTemplate:
    """Um modelo de protocolo da psicóloga logada."""
    return _get_protocolo_or_404(protocolo_id, db, current)


@router.put("/{protocolo_id}", response_model=ProtocoloOut)
def update_protocolo(
    protocolo_id: UUID,
    data: ProtocoloIn,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> ReportTemplate:
    """Laudos já criados não mudam: cada um guarda a cópia do modelo da
    época em `computed_json["modelo"]`."""
    modelo = _get_protocolo_or_404(protocolo_id, db, current)
    schema = data.schema_json.model_dump(mode="json")
    modelo.schema_json = schema
    modelo.name = schema["name"]
    modelo.version = (modelo.version or 1) + 1
    db.commit()
    db.refresh(modelo)
    return modelo


@router.delete("/{protocolo_id}", response_model=ProtocoloOut)
def arquivar_protocolo(
    protocolo_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> ReportTemplate:
    """Arquiva (não apaga): some da lista e de Novo Atendimento, mas os
    laudos feitos com ele continuam abrindo normalmente."""
    modelo = _get_protocolo_or_404(protocolo_id, db, current)
    modelo.arquivado = True
    db.commit()
    db.refresh(modelo)
    return modelo


@router.post("/{protocolo_id}/restaurar", response_model=ProtocoloOut)
def restaurar_protocolo(
    protocolo_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> ReportTemplate:
    """Tira o modelo do arquivo."""
    modelo = _get_protocolo_or_404(protocolo_id, db, current)
    modelo.arquivado = False
    db.commit()
    db.refresh(modelo)
    return modelo


@router.post("/{protocolo_id}/duplicar", response_model=ProtocoloOut, status_code=status.HTTP_201_CREATED)
def duplicar_protocolo(
    protocolo_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> ReportTemplate:
    """Cria uma cópia do modelo, com "(cópia)" no nome, para editar sem mexer no original."""
    original = _get_protocolo_or_404(protocolo_id, db, current)
    schema = dict(original.schema_json)
    schema["name"] = f"{original.name} (cópia)"[:255]
    copia = ReportTemplate(owner_id=current.id, name=schema["name"], version=1, schema_json=schema)
    db.add(copia)
    db.commit()
    db.refresh(copia)
    return copia
