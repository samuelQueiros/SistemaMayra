"""Fotos/documentos anexados para completar as pendências de um laudo. A IA
lê o arquivo em segundo plano e sugere valores para os campos que faltam;
nada vai para o laudo sem a psicóloga confirmar. Mesmo controle de acesso
dos pacientes: cada psicóloga só vê os seus."""

import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_psychologist
from app.api.patients import get_patient_or_404
from app.api.pendencias import catalogo_do_laudo, montar_pendencias
from app.api.reports import _get_report_do_psicologo
from app.core.database import get_db
from app.core.uploads import ler_upload
from app.models.ai_settings import AISettings
from app.models.patient_attachment import PatientAttachment
from app.models.psychologist import Psychologist
from app.models.report import Report
from app.services import laudo_ia_jobs
from app.services.ai import AIConfigurationError, resolve_ai_credentials
from app.services.ai.agentes.anexos import ler_anexo
from app.services.ai.agentes.extracao import ErroNaEtapaDaIA, motivo_do_erro
from app.services.ai.schemas import CampoPreenchido, ProtocoloPorIA
from app.services.imagens import ArquivoInvalido, imagens_para_ia, tipo_do_arquivo
from app.services.laudo_ia import CatalogoDoProtocolo, formatar_catalogo, respostas_para_answers
from app.services.storage import get_attachments_storage

router = APIRouter(prefix="/api/patients/{patient_id}/anexos", tags=["anexos"])

# Leitura parada há mais que isso (servidor reiniciou no meio) vira erro.
_LEITURA_PARADA_APOS = timedelta(minutes=5)


class AnexoOut(BaseModel):
    id: UUID
    nome: str
    mime: str
    secao: str | None
    status: str
    erro: str | None
    sugestoes: int
    created_at: datetime


def _saida(anexo: PatientAttachment) -> AnexoOut:
    return AnexoOut(
        id=anexo.id,
        nome=anexo.nome,
        mime=anexo.mime,
        secao=anexo.secao,
        status=anexo.status,
        erro=anexo.erro,
        sugestoes=len(anexo.sugestoes_json or []),
        created_at=anexo.created_at,
    )


def _anexo_or_404(patient_id: UUID, anexo_id: UUID, db: Session, current: Psychologist) -> PatientAttachment:
    patient = get_patient_or_404(patient_id, db, current)
    anexo = db.get(PatientAttachment, anexo_id)
    if anexo is None or anexo.patient_id != patient.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anexo não encontrado.")
    return anexo


def campos_que_faltam(db: Session, report: Report, catalogo: CatalogoDoProtocolo, secao: str | None) -> CatalogoDoProtocolo:
    """Só os campos ainda sem resposta (da seção, ou todos), com o rótulo
    amigável da pendência — é isso que a IA procura no documento."""
    pendencias = montar_pendencias(db, report, catalogo)
    por_id = {c.id: c for c in catalogo.campos}
    campos = []
    for grupo in pendencias["grupos"]:
        if secao and grupo["chave"] != secao:
            continue
        for item in grupo["itens"]:
            if item["situacao"]:
                continue
            for sub in item["campos"]:
                original = por_id[sub["id"]]
                campos.append(original.model_copy(update={"secao": grupo["titulo"], "rotulo": item["rotulo"]}))
    return CatalogoDoProtocolo(campos=campos)


def _ler_em_segundo_plano(*, bind, anexo_id: UUID, conteudo: bytes, credenciais: dict) -> None:
    with Session(bind=bind) as db:
        anexo = db.get(PatientAttachment, anexo_id)
        report = db.get(Report, anexo.report_id)
        try:
            catalogo = catalogo_do_laudo(report)
            faltam = campos_que_faltam(db, report, catalogo, anexo.secao) if catalogo else CatalogoDoProtocolo(campos=[])
            if not faltam.campos:
                anexo.sugestoes_json, anexo.status = [], "pronto"
                db.commit()
                return
            leitura = ler_anexo(
                imagens=imagens_para_ia(conteudo, anexo.mime),
                nome=anexo.nome,
                catalogo_texto=formatar_catalogo(faltam),
                **credenciais,
            )
            # Mesma régua do Laudo por IA: fora do catálogo ou opção inválida é descartado.
            validos, _ = respostas_para_answers(
                ProtocoloPorIA(estudo_de_caso="", campos=[CampoPreenchido(id=c.id, valor=c.valor) for c in leitura.campos]), faltam
            )
            trechos = {c.id: c.trecho for c in leitura.campos}
            anexo.sugestoes_json = [
                {"campo_id": campo_id, "valor": valor, "trecho": trechos.get(campo_id, "")[:200]}
                for campo_id, valor in validos.items()
                if isinstance(valor, str)
            ]
            anexo.status = "pronto"
        except (ErroNaEtapaDaIA, ArquivoInvalido) as exc:
            anexo.status, anexo.erro = "erro", str(exc)
        except Exception as exc:  # noqa: BLE001 - vira mensagem na tela
            anexo.status, anexo.erro = "erro", f"Não foi possível ler '{anexo.nome}' ({motivo_do_erro(exc)})."
        db.commit()


@router.post("", response_model=AnexoOut, status_code=status.HTTP_202_ACCEPTED)
def enviar_anexo(
    patient_id: UUID,
    arquivo: UploadFile = File(...),
    report_id: UUID = Form(...),
    secao: str | None = Form(default=None, max_length=200),
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> AnexoOut:
    patient = get_patient_or_404(patient_id, db, current)
    report = _get_report_do_psicologo(report_id, db, current)
    if report.patient_id != patient.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Protocolo não encontrado.")
    nome = (arquivo.filename or "anexo").strip()[:255]
    conteudo = ler_upload(arquivo)
    try:
        mime = tipo_do_arquivo(nome, conteudo)
    except ArquivoInvalido as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    ai_settings = db.query(AISettings).filter(AISettings.owner_id == current.id).first()
    try:
        provider, model, api_key = resolve_ai_credentials(ai_settings)
    except AIConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    extensao = "." + nome.rsplit(".", 1)[-1].lower()
    chave = f"{patient.id}/{uuid.uuid4()}{extensao}"
    get_attachments_storage().save(chave, conteudo)
    anexo = PatientAttachment(
        patient_id=patient.id,
        report_id=report.id,
        created_by_id=current.id,
        nome=nome,
        mime=mime,
        file_path=chave,
        secao=secao or None,
        status="analisando",
    )
    db.add(anexo)
    db.commit()
    laudo_ia_jobs.em_segundo_plano(
        lambda: _ler_em_segundo_plano(
            bind=db.get_bind(),
            anexo_id=anexo.id,
            conteudo=conteudo,
            credenciais={"provider": provider, "model": model, "api_key": api_key},
        ),
        f"Leitura do anexo {anexo.id}",
    )
    return _saida(anexo)


@router.get("", response_model=list[AnexoOut])
def listar_anexos(
    patient_id: UUID,
    report_id: UUID | None = None,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> list[AnexoOut]:
    patient = get_patient_or_404(patient_id, db, current)
    consulta = db.query(PatientAttachment).filter(PatientAttachment.patient_id == patient.id)
    if report_id is not None:
        consulta = consulta.filter(PatientAttachment.report_id == report_id)
    anexos = consulta.order_by(PatientAttachment.created_at).all()
    limite = datetime.now(timezone.utc) - _LEITURA_PARADA_APOS
    parados = [
        a for a in anexos
        if a.status == "analisando" and (a.created_at.replace(tzinfo=a.created_at.tzinfo or timezone.utc)) < limite
    ]
    for anexo in parados:
        anexo.status, anexo.erro = "erro", f"A leitura de '{anexo.nome}' foi interrompida. Apague e anexe de novo."
    if parados:
        db.commit()
    return [_saida(a) for a in anexos]


@router.get("/{anexo_id}/arquivo")
def baixar_anexo(
    patient_id: UUID, anexo_id: UUID, db: Session = Depends(get_db), current: Psychologist = Depends(get_current_psychologist)
) -> Response:
    anexo = _anexo_or_404(patient_id, anexo_id, db, current)
    return Response(content=get_attachments_storage().read(anexo.file_path), media_type=anexo.mime)


@router.delete("/{anexo_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_anexo(
    patient_id: UUID, anexo_id: UUID, db: Session = Depends(get_db), current: Psychologist = Depends(get_current_psychologist)
) -> None:
    anexo = _anexo_or_404(patient_id, anexo_id, db, current)
    get_attachments_storage().delete(anexo.file_path)
    db.delete(anexo)
    db.commit()
