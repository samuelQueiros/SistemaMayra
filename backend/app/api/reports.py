from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_psychologist
from app.api.patients import get_patient_or_404
from app.core.cid_codes import CID_CODES
from app.core.database import get_db
from app.models.patient import Patient
from app.models.psychologist import Psychologist
from app.models.report import Report
from app.models.report_change_log import ReportChangeLog
from app.models.report_template import ReportTemplate
from app.models.ai_settings import AISettings
from app.rules_engine import RulesEngineError, calculate_report
from app.schemas.report import (
    ClinicalSections,
    LogDeEdicaoOut,
    ConclusionRequest,
    ConclusionResponse,
    ReportAnswersUpdate,
    ReportChangeLogOut,
    ReportCreate,
    ReportEditUpdate,
    ReportOut,
    ReportTextUpdate,
)
from app.services.ai import (
    AIConfigurationError,
    generate_conclusion_and_interventions,
    generate_report_text,
    resolve_ai_credentials,
)
from app.api.documents import MIME_DOCX, nome_de_arquivo_seguro, resposta_de_arquivo
from app.services.laudo_documento import DocumentoInvalidoError, html_para_docx
from app.services.pdf import RULE_TYPES_COM_HTML_PRONTO, render_report_pdf
from app.services.storage import get_reports_storage

router = APIRouter(tags=["reports"])


def _get_template_or_404(template_id: UUID, db: Session, current: Psychologist) -> ReportTemplate:
    template = db.get(ReportTemplate, template_id)
    if template is None or template.owner_id != current.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo não encontrado")
    return template


def _get_report_do_psicologo(report_id: UUID, db: Session, current: Psychologist) -> Report:
    report = db.get(Report, report_id)
    if report is None or report.patient.owner_id != current.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Protocolo não encontrado. Ele pode ter sido excluído ou pertencer a outra conta.")
    return report


@router.post(
    "/api/patients/{patient_id}/reports",
    response_model=ReportOut,
    status_code=status.HTTP_201_CREATED,
)
def create_report(
    patient_id: UUID,
    data: ReportCreate,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Report:
    patient = get_patient_or_404(patient_id, db, current)
    template = _get_template_or_404(data.template_id, db, current)

    try:
        computed = calculate_report(
            template.schema_json,
            data.answers,
            birth_date=patient.birth_date,
            evaluation_date=data.evaluation_date,
        )
    except RulesEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    report = Report(
        patient_id=patient.id,
        template_id=template.id,
        answers_json=data.answers,
        computed_json=computed,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/api/patients/{patient_id}/reports", response_model=list[ReportOut])
def list_reports(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> list[Report]:
    patient = get_patient_or_404(patient_id, db, current)
    return (
        db.query(Report)
        .filter(Report.patient_id == patient.id)
        .order_by(Report.created_at.desc())
        .all()
    )


@router.get("/api/reports/{report_id}", response_model=ReportOut)
def get_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Report:
    return _get_report_do_psicologo(report_id, db, current)


@router.post("/api/reports/{report_id}/generate-text", response_model=ReportOut)
def generate_text(
    report_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Report:
    report = _get_report_do_psicologo(report_id, db, current)
    if report.computed_json is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este protocolo ainda não tem pontuação calculada.",
        )

    template = db.get(ReportTemplate, report.template_id)
    ai_settings = db.query(AISettings).filter(AISettings.owner_id == current.id).first()

    try:
        provider, model, api_key = resolve_ai_credentials(ai_settings)
        sections = generate_report_text(
            provider=provider,
            model=model,
            api_key=api_key,
            template_name=template.name,
            patient_name=report.patient.name,
            schema=template.schema_json,
            answers=report.answers_json,
            computed=report.computed_json,
        )
    except AIConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except Exception as exc:
        # Erros do próprio provedor de IA (chave inválida, modelo
        # inexistente, indisponibilidade, etc.) não devem virar um 500 sem
        # explicação — a psicóloga precisa saber que é algo para revisar
        # em "Configurações", não um bug do sistema.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Não foi possível gerar o texto com o provedor de IA configurado "
                f"({provider}/{model}). Verifique a chave de API e o modelo em "
                f"\"Configurações\". Detalhe técnico: {exc}"
            ),
        ) from exc

    report.generated_text = sections.como_texto()
    db.commit()
    db.refresh(report)
    return report


@router.post("/api/reports/{report_id}/generate-conclusion", response_model=ConclusionResponse)
def generate_conclusion(
    report_id: UUID,
    data: ConclusionRequest,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> ConclusionResponse:
    """Gera, com IA, as Considerações Finais e as Sugestões De Intervenção
    individualizadas a partir dos dados deste paciente (pontos 2 e 3 da
    revisão de relatórios) — usado pelo formulário standalone
    (formulario-novo-paciente.html), que monta o resumo curado enviado em
    `data` a partir do que a psicóloga já preencheu para este atendimento.
    Só confirma que o laudo pertence à psicóloga logada; não lê nem grava
    `answers_json`/`generated_text` — o formulário decide onde usar o
    texto retornado."""

    _get_report_do_psicologo(report_id, db, current)
    ai_settings = db.query(AISettings).filter(AISettings.owner_id == current.id).first()

    try:
        provider, model, api_key = resolve_ai_credentials(ai_settings)
        secoes = generate_conclusion_and_interventions(
            provider=provider,
            model=model,
            api_key=api_key,
            patient_name=data.patient_name,
            estudo_de_caso=data.estudo_de_caso,
            observacoes_clinicas=data.observacoes_clinicas,
            habilidades_avaliadas=data.habilidades_avaliadas,
            protocolos_utilizados=data.protocolos_utilizados,
            hipotese_selecionada=data.hipotese_selecionada,
        )
    except AIConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Não foi possível gerar o texto com o provedor de IA configurado "
                f"({provider}/{model}). Verifique a chave de API e o modelo em "
                f"\"Configurações\". Detalhe técnico: {exc}"
            ),
        ) from exc

    return ConclusionResponse(
        consideracoes_finais=secoes.como_texto_consideracoes(),
        sugestoes_intervencao=secoes.como_texto_sugestoes(),
    )


@router.put("/api/reports/{report_id}/text", response_model=ReportOut)
def update_text(
    report_id: UUID,
    data: ReportTextUpdate,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Report:
    # A psicóloga revisa/edita o texto gerado pela IA antes da exportação
    # final (SPEC.md seção 5: nunca exportar sem revisão humana).
    report = _get_report_do_psicologo(report_id, db, current)
    report.generated_text = data.generated_text
    db.commit()
    db.refresh(report)
    return report


@router.put("/api/reports/{report_id}/answers", response_model=ReportOut)
def update_answers(
    report_id: UUID,
    data: ReportAnswersUpdate,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Report:
    """Autosave: sincroniza com o banco cada campo alterado no formulário
    standalone enquanto a psicóloga preenche, em vez de ficar só no
    localStorage do navegador (ver ENTREGAS.md)."""
    report = _get_report_do_psicologo(report_id, db, current)
    report.answers_json = data.answers
    db.commit()
    db.refresh(report)
    return report


@router.patch("/api/reports/{report_id}", response_model=ReportOut)
def edit_report(
    report_id: UUID,
    data: ReportEditUpdate,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Report:
    """Correção manual do que aparece no histórico (nome do modelo,
    classificação) — cada mudança de valor vira uma entrada de log,
    nunca é sobrescrita silenciosamente."""

    report = _get_report_do_psicologo(report_id, db, current)

    for field, new_value in data.model_dump(exclude_unset=True).items():
        old_value = getattr(report, field)
        if old_value == new_value:
            continue
        db.add(
            ReportChangeLog(
                report_id=report.id,
                psychologist_id=current.id,
                field=field,
                old_value=old_value,
                new_value=new_value,
            )
        )
        setattr(report, field, new_value)

    db.commit()
    db.refresh(report)
    return report


@router.get("/api/cid-codes")
def list_cid_codes(_: Psychologist = Depends(get_current_psychologist)) -> list[dict]:
    """Lista curta de hipóteses diagnósticas comuns com o CID-11
    correspondente, para a tela de seções clínicas do laudo (ver
    ENTREGAS.md — "PDF completo"). Não é uma tabela oficial completa do
    CID-11 — a psicóloga pode digitar qualquer outra hipótese como texto
    livre."""
    return CID_CODES


@router.patch("/api/reports/{report_id}/clinical-sections", response_model=ReportOut)
def update_clinical_sections(
    report_id: UUID,
    data: ClinicalSections,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Report:
    """Salva as seções clínicas opcionais do PDF completo (anamnese,
    histórico, hipóteses diagnósticas com CID, plano de intervenção etc.).
    Endpoint separado do `PATCH /api/reports/{id}` (que já tem seu próprio
    log de auditoria testado) para não arriscar mudar aquele comportamento."""

    report = _get_report_do_psicologo(report_id, db, current)
    report.clinical_sections_json = data.model_dump(exclude_none=True)
    db.commit()
    db.refresh(report)
    return report


LIMITE_DE_LOGS = 500


@router.get("/api/logs", response_model=list[LogDeEdicaoOut])
def list_all_logs(
    patient_id: UUID | None = None,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> list[LogDeEdicaoOut]:
    """Todas as edições de relatórios da psicóloga (mais recentes primeiro),
    com filtro opcional por paciente — página "Ver Logs" do menu lateral."""
    consulta = (
        db.query(ReportChangeLog)
        .join(Report, ReportChangeLog.report_id == Report.id)
        .join(Patient, Report.patient_id == Patient.id)
        .filter(Patient.owner_id == current.id)
    )
    if patient_id is not None:
        consulta = consulta.filter(Patient.id == patient_id)
    logs = consulta.order_by(ReportChangeLog.created_at.desc()).limit(LIMITE_DE_LOGS).all()
    return [
        LogDeEdicaoOut(
            id=log.id,
            field=log.field,
            old_value=log.old_value,
            new_value=log.new_value,
            created_at=log.created_at,
            psychologist_name=log.psychologist.name,
            report_id=log.report.id,
            report_created_at=log.report.created_at,
            patient_id=log.report.patient.id,
            patient_name=log.report.patient.name,
            template_name=log.report.template_name_override or log.report.template.name,
        )
        for log in logs
    ]


@router.get("/api/reports/{report_id}/logs", response_model=list[ReportChangeLogOut])
def list_report_logs(
    report_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> list[ReportChangeLogOut]:
    report = _get_report_do_psicologo(report_id, db, current)
    return [
        ReportChangeLogOut(
            id=log.id,
            field=log.field,
            old_value=log.old_value,
            new_value=log.new_value,
            created_at=log.created_at,
            psychologist_name=log.psychologist.name,
        )
        for log in report.change_logs
    ]


@router.get("/api/reports/{report_id}/pdf")
def download_pdf(
    report_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Response:
    report = _get_report_do_psicologo(report_id, db, current)
    if report.computed_json is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este protocolo ainda não tem pontuação calculada.",
        )

    template = db.get(ReportTemplate, report.template_id)
    chave_pdf = render_report_pdf(
        patient=report.patient, template=template, report=report, psychologist=current
    )

    report.pdf_path = chave_pdf
    db.commit()

    conteudo = get_reports_storage().read(chave_pdf)
    nome_arquivo = nome_de_arquivo_seguro(f"laudo_{report.patient.name}_{report.id}", "pdf")
    return Response(
        content=conteudo,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


@router.get("/api/reports/{report_id}/docx")
def download_docx(
    report_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Response:
    """Word (.docx) editável do laudo do formulário fixo, a partir do mesmo
    HTML salvo em `generated_text` que gera o PDF."""
    report = _get_report_do_psicologo(report_id, db, current)
    template = db.get(ReportTemplate, report.template_id)
    if template.schema_json.get("rule_type") not in RULE_TYPES_COM_HTML_PRONTO or not report.generated_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O relatório deste protocolo ainda não foi gerado. Abra o protocolo e clique em \"Salvar Protocolo\".",
        )
    try:
        conteudo = html_para_docx(report.generated_text)
    except DocumentoInvalidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este protocolo foi salvo num formato antigo. Abra o protocolo e clique em \"Salvar Protocolo\" para gerar o Word.",
        ) from exc
    nome = nome_de_arquivo_seguro(f"laudo_{report.patient.name}", "docx")
    return resposta_de_arquivo(conteudo, MIME_DOCX, nome)
