"""Pendências de um laudo (o que faltou depois do Laudo por IA) — ver
app/services/pendencias.py. Mesmo controle de acesso dos laudos: cada
psicóloga só vê os próprios."""

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy.orm import Session

from app.api.deps import get_current_psychologist
from app.api.patients import get_patient_or_404
from app.api.reports import _get_report_do_psicologo
from app.core.database import get_db
from app.models.patient_attachment import PatientAttachment
from app.models.psychologist import Psychologist
from app.models.report import Report
from app.services.laudo_ia import CatalogoDoProtocolo
from app.services.pendencias import ESCALAS, Pendencias

router = APIRouter(tags=["pendencias"])

SEM_CATALOGO = "Este laudo não guardou os campos do protocolo. Envie o catálogo do formulário."


def catalogo_do_laudo(report: Report) -> CatalogoDoProtocolo | None:
    dados = (report.computed_json or {}).get("catalogo")
    return CatalogoDoProtocolo.model_validate(dados) if dados else None


def sugestoes_dos_anexos(db: Session, report: Report) -> list[dict]:
    anexos = (
        db.query(PatientAttachment)
        .filter(PatientAttachment.report_id == report.id, PatientAttachment.status == "pronto")
        .order_by(PatientAttachment.created_at)
        .all()
    )
    return [
        {**sugestao, "anexo_id": str(anexo.id), "anexo_nome": anexo.nome}
        for anexo in anexos
        for sugestao in anexo.sugestoes_json or []
    ]


def montar_pendencias(db: Session, report: Report, catalogo: CatalogoDoProtocolo) -> dict:
    computed = report.computed_json or {}
    return Pendencias(
        catalogo,
        report.answers_json,
        report.patient.dados_complementares,
        [d.get("tipo", "") for d in computed.get("documentos", [])],
        computed.get("escalas_adicionadas", []),
        sugestoes_dos_anexos(db, report),
    ).montar()


@router.get("/api/reports/{report_id}/pendencias")
def ver_pendencias(
    report_id: UUID, db: Session = Depends(get_db), current: Psychologist = Depends(get_current_psychologist)
) -> dict:
    report = _get_report_do_psicologo(report_id, db, current)
    catalogo = catalogo_do_laudo(report)
    if catalogo is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=SEM_CATALOGO)
    return montar_pendencias(db, report, catalogo)


@router.post("/api/reports/{report_id}/pendencias")
def guardar_catalogo_e_ver_pendencias(
    report_id: UUID,
    catalogo: CatalogoDoProtocolo,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> dict:
    """Laudos criados antes da cópia do catálogo: a tela lê o catálogo no
    formulário (modo=catalogo) e manda aqui uma vez."""
    report = _get_report_do_psicologo(report_id, db, current)
    report.computed_json = {**(report.computed_json or {}), "catalogo": catalogo.model_dump()}
    db.commit()
    return montar_pendencias(db, report, catalogo)


class EscalasAplicadas(BaseModel):
    escalas: list[str]


@router.put("/api/reports/{report_id}/escalas-aplicadas")
def marcar_escalas_aplicadas(
    report_id: UUID,
    dados: EscalasAplicadas,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> dict:
    """"Também apliquei": escalas sem PDF que entram nas pendências."""
    report = _get_report_do_psicologo(report_id, db, current)
    validas = {e.chave for e in ESCALAS}
    if not set(dados.escalas) <= validas:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Escala desconhecida.")
    report.computed_json = {**(report.computed_json or {}), "escalas_adicionadas": sorted(set(dados.escalas))}
    db.commit()
    catalogo = catalogo_do_laudo(report)
    if catalogo is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=SEM_CATALOGO)
    return montar_pendencias(db, report, catalogo)


# --- dados complementares do paciente (salvamento automático) ------------------

IdDoCampo = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_\-]+$", max_length=120)]
_TAMANHO_MAXIMO_DO_VALOR = 8000


class DadoComplementar(BaseModel):
    valor: str | bool | float | None = None
    situacao: Literal["preenchido", "nao_se_aplica", "nao_informado"]
    origem: Literal["digitado", "anexo"] = "digitado"
    anexo_id: UUID | None = None


class DadosComplementaresIn(BaseModel):
    # None apaga o campo (ex.: desfazer "Não se aplica").
    campos: dict[IdDoCampo, DadoComplementar | None] = Field(max_length=500)


@router.patch("/api/patients/{patient_id}/dados-complementares")
def salvar_dados_complementares(
    patient_id: UUID,
    dados: DadosComplementaresIn,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> dict:
    """Mescla, campo a campo, o que a psicóloga confirmou nas pendências.
    Fica no paciente e é reaproveitado nos próximos laudos."""
    patient = get_patient_or_404(patient_id, db, current)
    anexos_citados = {d.anexo_id for d in dados.campos.values() if d and d.anexo_id}
    if anexos_citados:
        do_paciente = {
            a.id for a in db.query(PatientAttachment.id).filter(
                PatientAttachment.patient_id == patient.id, PatientAttachment.id.in_(anexos_citados)
            )
        }
        if anexos_citados - do_paciente:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Anexo não encontrado para este paciente.")

    atuais = dict(patient.dados_complementares or {})
    agora = datetime.now(timezone.utc).isoformat()
    for campo, dado in dados.campos.items():
        if dado is None:
            atuais.pop(campo, None)
            continue
        if isinstance(dado.valor, str) and len(dado.valor) > _TAMANHO_MAXIMO_DO_VALOR:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Texto longo demais para um campo.")
        atuais[campo] = {**dado.model_dump(mode="json"), "atualizado_em": agora}
    patient.dados_complementares = atuais
    db.commit()
    return {"dados": atuais}
