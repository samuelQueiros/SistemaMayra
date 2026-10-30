"""Pendências de um laudo (o que faltou depois do Laudo por IA) — ver
app/services/pendencias.py. Mesmo controle de acesso dos laudos: cada
psicóloga só vê os próprios."""

from datetime import datetime, timezone
from functools import partial
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy.orm import Session, defer

from app.api.deps import get_current_psychologist
from app.api.patients import get_patient_or_404
from app.api.reports import _get_report_do_psicologo
from app.core.database import get_db
from app.models.ai_settings import AISettings
from app.models.patient_attachment import PatientAttachment
from app.models.psychologist import Psychologist
from app.models.report import Report
from app.services import laudo_ia_jobs
from app.services.ai import AIConfigurationError, resolve_ai_credentials
from app.services.ai.agentes import (
    DocumentoExtraido,
    documentos_em_texto,
    integrar_dados_ao_estudo_de_caso,
    redigir_estudo_de_caso,
)
from app.services.ai.agentes.extracao import motivo_do_erro
from app.services.laudo_ia import CatalogoDoProtocolo, TAMANHO_MAXIMO_TEXTO
from app.services.laudo_ia_jobs import Andamento
from app.services.pendencias import (
    ESCALAS,
    Pendencias,
    aplicar_dados_confirmados,
    campos_novos_para_o_estudo,
    dados_confirmados_como_documento,
    estudo_de_caso_editado,
)

router = APIRouter(tags=["pendencias"])

SEM_CATALOGO = "Este laudo não guardou os campos do protocolo. Envie o catálogo do formulário."


def catalogo_do_laudo(report: Report) -> CatalogoDoProtocolo | None:
    """Catálogo de campos do protocolo guardado no laudo (`computed_json.catalogo`), ou None em laudos
    anteriores ao catálogo."""
    dados = (report.computed_json or {}).get("catalogo")
    return CatalogoDoProtocolo.model_validate(dados) if dados else None


def sugestoes_dos_anexos(db: Session, report: Report) -> list[dict]:
    """Sugestões que a IA tirou dos anexos prontos, para a psicóloga confirmar uma a uma."""
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
    """Calcula as pendências do laudo (`services/pendencias.py`) com as respostas atuais, os dados
    confirmados do paciente, as escalas já aplicadas e as sugestões dos anexos."""
    computed = report.computed_json or {}
    resultado = Pendencias(
        catalogo,
        report.answers_json,
        report.patient.dados_complementares,
        [d.get("tipo", "") for d in computed.get("documentos", [])],
        computed.get("escalas_adicionadas", []),
        sugestoes_dos_anexos(db, report),
    ).montar()
    excluidos = report.answers_json.get("__metodosExcluidos", [])
    resultado["metodos"] = [
        {"chave": e.chave, "titulo": e.titulo, "incluido": e.chave not in excluidos} for e in ESCALAS
    ]
    resultado["estudo_de_caso"] = {"editado": estudo_de_caso_editado(report.answers_json, computed)}
    return resultado


@router.get("/api/reports/{report_id}/pendencias")
def ver_pendencias(
    report_id: UUID, db: Session = Depends(get_db), current: Psychologist = Depends(get_current_psychologist)
) -> dict:
    """Pendências de um laudo, agrupadas por seção."""
    report = _get_report_do_psicologo(report_id, db, current, defer(Report.generated_text))
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
    report = _get_report_do_psicologo(report_id, db, current, defer(Report.generated_text))
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
    """ "Também apliquei": escalas sem PDF que entram nas pendências."""
    report = _get_report_do_psicologo(report_id, db, current, defer(Report.generated_text))
    validas = {e.chave for e in ESCALAS}
    if not set(dados.escalas) <= validas:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Escala desconhecida.")
    report.computed_json = {**(report.computed_json or {}), "escalas_adicionadas": sorted(set(dados.escalas))}
    db.commit()
    catalogo = catalogo_do_laudo(report)
    if catalogo is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=SEM_CATALOGO)
    return montar_pendencias(db, report, catalogo)


@router.put("/api/reports/{report_id}/metodos-excluidos")
def excluir_metodos(
    report_id: UUID,
    dados: EscalasAplicadas,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> dict:
    """Guarda quais escalas a psicóloga tirou do relatório (`answers_json.__metodosExcluidos`). Os dados
    da escala continuam salvos; o gerador do documento só omite os blocos."""
    report = _get_report_do_psicologo(report_id, db, current, defer(Report.generated_text))
    catalogo = catalogo_do_laudo(report)
    if catalogo is None:
        raise HTTPException(status_code=409, detail=SEM_CATALOGO)
    if not set(dados.escalas) <= {e.chave for e in ESCALAS}:
        raise HTTPException(status_code=400, detail="Método desconhecido.")
    report.answers_json = {**report.answers_json, "__metodosExcluidos": sorted(set(dados.escalas))}
    db.commit()
    return montar_pendencias(db, report, catalogo)


# --- dados complementares do paciente (salvamento automático) ------------------

IdDoCampo = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_\-]+$", max_length=120)]
_TAMANHO_MAXIMO_DO_VALOR = 8000


class DadoComplementar(BaseModel):
    """Um campo confirmado pela psicóloga: valor e situação (preenchido, não se aplica, não informado)."""

    valor: str | bool | float | None = None
    situacao: Literal["preenchido", "nao_se_aplica", "nao_informado"]
    origem: Literal["digitado", "anexo"] = "digitado"
    anexo_id: UUID | None = None


class DadosComplementaresIn(BaseModel):
    """Dados confirmados, por id de campo do catálogo (até 500 por pedido)."""

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
            a.id
            for a in db.query(PatientAttachment.id).filter(
                PatientAttachment.patient_id == patient.id, PatientAttachment.id.in_(anexos_citados)
            )
        }
        if anexos_citados - do_paciente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Anexo não encontrado para este paciente."
            )

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


# --- atualizar o laudo com os dados confirmados ---------------------------------


class AtualizarLaudoIn(BaseModel):
    """Pedido de "Atualizar relatório"; `reescrever_estudo` força reescrever o estudo de caso do zero."""

    # Inclui os dados novos mesmo no estudo de caso editado à mão (pedido explícito).
    reescrever_estudo: bool = False


def _reescrever_estudo(andamento: Andamento, *, bind, report_id: UUID, paciente: str, credenciais: dict) -> None:
    """ "Atualizar relatório": a IA recebe só o estudo de caso atual + os dados
    novos e os encaixa no texto (coerente com o que já foi escrito, sem os
    documentos do caso). Sem estudo anterior, redige do zero sobre o JSON dos
    PDFs já lidos (computed_json.documentos) — nunca relê os PDFs."""
    with Session(bind=bind) as db:
        report = db.get(Report, report_id)
        computed = dict(report.computed_json or {})
        catalogo = catalogo_do_laudo(report)
        dados = report.patient.dados_complementares or {}
        estudo_atual = (report.answers_json.get("estudoCaso") or "").strip()
        novos = campos_novos_para_o_estudo(
            catalogo, report.answers_json, dados, computed.get("estudo_campos_integrados")
        )
        try:
            if estudo_atual:
                andamento.mensagem("Incluindo os dados novos no estudo de caso…")
                texto = dados_confirmados_como_documento(catalogo, report.answers_json, novos)["respostas"]
                estudo = integrar_dados_ao_estudo_de_caso(
                    paciente=paciente,
                    estudo_atual=estudo_atual,
                    dados_novos="\n".join(f"- {r['pergunta']}: {r['resposta']}" for r in texto),
                    observacoes=computed.get("observacoes"),
                    **credenciais,
                )
            else:
                andamento.mensagem("Escrevendo o estudo de caso com os dados novos…")
                documentos = [DocumentoExtraido.model_validate(d) for d in computed.get("documentos", [])]
                if novos:
                    documentos.append(
                        DocumentoExtraido.model_validate(
                            dados_confirmados_como_documento(catalogo, report.answers_json, novos)
                        )
                    )
                estudo = redigir_estudo_de_caso(
                    paciente=paciente,
                    documentos_texto=documentos_em_texto(documentos),
                    observacoes=computed.get("observacoes"),
                    **credenciais,
                )
        except Exception as exc:  # noqa: BLE001 - vira mensagem no andamento
            andamento.falhar(
                f"Os dados novos já estão no relatório, mas não foi possível atualizar o estudo de caso ({motivo_do_erro(exc)}). "
                "Tente de novo ou gere o documento assim mesmo."
            )
            return
        estudo = estudo.strip()[: TAMANHO_MAXIMO_TEXTO * 2]
        report.answers_json = {**report.answers_json, "estudoCaso": estudo}
        report.computed_json = {
            **computed,
            "estudo_de_caso_ia": estudo,
            "estudo_campos_integrados": sorted(set(computed.get("estudo_campos_integrados", [])) | novos),
        }
        db.commit()
    andamento.concluir(report_id)


@router.post("/api/reports/{report_id}/atualizar")
def atualizar_laudo(
    report_id: UUID,
    pedido: AtualizarLaudoIn,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> dict:
    """1) aplica no laudo os dados confirmados (sem IA); 2) se há dados novos
    das seções que alimentam o estudo de caso e ele não foi editado à mão (ou
    se a psicóloga pedir), a IA os encaixa no estudo atual em segundo plano.
    A tela depois gera o documento pelo formulário (sem IA)."""
    from app.api.laudo_ia import _descricao_do_paciente  # evita import circular

    report = _get_report_do_psicologo(report_id, db, current, defer(Report.generated_text))
    catalogo = catalogo_do_laudo(report)
    if catalogo is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=SEM_CATALOGO)
    editado = estudo_de_caso_editado(report.answers_json, report.computed_json)
    novas, aplicados = aplicar_dados_confirmados(catalogo, report.answers_json, report.patient.dados_complementares)
    report.answers_json = novas
    db.commit()

    integrados = (report.computed_json or {}).get("estudo_campos_integrados")
    novos = campos_novos_para_o_estudo(catalogo, novas, report.patient.dados_complementares, integrados)
    sem_estudo = not (novas.get("estudoCaso") or "").strip()
    # Sem estudo anterior (laudo antigo), só a pedido; com estudo, só se há o que incluir.
    if sem_estudo:
        deve = pedido.reescrever_estudo
    else:
        deve = bool(novos) and (pedido.reescrever_estudo or not editado)
    if not deve:
        return {
            "job_id": None,
            "campos_aplicados": len(aplicados),
            "estudo": "mantido_editado" if novos and editado else "sem_mudanca",
        }

    ai_settings = db.query(AISettings).filter(AISettings.owner_id == current.id).first()
    try:
        provider, model, api_key = resolve_ai_credentials(ai_settings)
    except AIConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    job = laudo_ia_jobs.criar(owner_id=current.id, patient_id=report.patient_id, nomes_dos_arquivos=[])
    laudo_ia_jobs.executar(
        job,
        partial(
            _reescrever_estudo,
            bind=db.get_bind(),
            report_id=report.id,
            paciente=_descricao_do_paciente(report.patient),
            credenciais={"provider": provider, "model": model, "api_key": api_key},
        ),
    )
    return {"job_id": job["id"], "campos_aplicados": len(aplicados), "estudo": "reescrevendo"}
