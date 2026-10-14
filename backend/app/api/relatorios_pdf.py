"""Relatório por IA a partir de PDFs de respostas de formulários (Google
Forms) — substitui o antigo "PDF consolidado" do Histórico. A psicóloga
anexa de 1 a 6 PDFs; a IA lê perguntas e respostas e devolve o relatório
estruturado por área/tema (`services/ai/schemas.py::RelatorioPorPdfs`). O
resultado vira um laudo comum (`Report`) do template interno
"relatorio_ia_pdf": `computed_json["relatorio"]` é editado na tela de
revisão e o HTML final, montado no navegador no padrão do sistema, vai para
`generated_text` (PDF/Word do Histórico como os demais)."""

import uuid
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_psychologist
from app.api.documents import nome_de_arquivo_seguro
from app.api.patients import get_patient_or_404
from app.core.database import get_db
from app.models.ai_settings import AISettings
from app.models.psychologist import Psychologist
from app.models.report import Report
from app.models.report_template import ReportTemplate
from app.schemas.report import ReportOut
from app.services.ai import AIConfigurationError, generate_report_from_form_pdfs, resolve_ai_credentials
from app.services.ai.schemas import RelatorioPorPdfs
from app.services.document_text import DocumentTextError, extrair_texto_pdf
from app.services.storage import get_form_pdfs_storage

router = APIRouter(tags=["relatorios-pdf"])

RULE_TYPE = "relatorio_ia_pdf"
NOME_TEMPLATE = "Relatório Por IA (PDFs Dos Formulários)"
MAXIMO_DE_ARQUIVOS = 6
TAMANHO_MAXIMO_PDF = 15 * 1024 * 1024


def _template_interno(db: Session, current: Psychologist) -> ReportTemplate:
    """"Porta-laudo" fixo por psicóloga (mesma ideia do custom_form do
    protocolo padrão). Idempotente."""
    for template in db.query(ReportTemplate).filter(ReportTemplate.owner_id == current.id).all():
        if template.schema_json.get("rule_type") == RULE_TYPE:
            return template
    template = ReportTemplate(
        owner_id=current.id,
        name=NOME_TEMPLATE,
        version=1,
        schema_json={"rule_type": RULE_TYPE, "name": NOME_TEMPLATE},
    )
    db.add(template)
    db.flush()
    return template


def _idade(nascimento: date) -> str:
    hoje = date.today()
    meses = (hoje.year - nascimento.year) * 12 + hoje.month - nascimento.month - (hoje.day < nascimento.day)
    anos, meses = divmod(max(meses, 0), 12)
    return f"{anos} anos e {meses} meses"


def ler_pdfs_enviados(arquivos: list[UploadFile], maximo: int) -> list[dict]:
    """Valida e lê os PDFs enviados (nome, bytes e texto extraído)."""
    if not arquivos:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Anexe pelo menos um PDF.")
    if len(arquivos) > maximo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Anexe no máximo {maximo} PDFs por relatório.",
        )
    pdfs: list[dict] = []
    for arquivo in arquivos:
        nome = arquivo.filename or "formulario.pdf"
        conteudo = arquivo.file.read(TAMANHO_MAXIMO_PDF + 1)
        if not nome.lower().endswith(".pdf") or not conteudo.startswith(b"%PDF"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{nome}' não é um PDF. Exporte as respostas do Google Forms em PDF e tente de novo.",
            )
        if len(conteudo) > TAMANHO_MAXIMO_PDF:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"'{nome}' passa de 15 MB.",
            )
        try:
            texto = extrair_texto_pdf(conteudo)
        except DocumentTextError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Não foi possível ler '{nome}'. O PDF pode estar corrompido."
            ) from exc
        pdfs.append({"nome": nome, "conteudo": conteudo, "texto": texto})
    return pdfs


def guardar_pdfs(patient_id, pdfs: list[dict]) -> list[dict]:
    storage = get_form_pdfs_storage()
    guardados = []
    for pdf in pdfs:
        chave = f"{patient_id}/{uuid.uuid4()}.pdf"
        storage.save(chave, pdf["conteudo"])
        guardados.append({"nome": pdf["nome"], "chave": chave})
    return guardados


@router.post("/api/patients/{patient_id}/relatorios-pdf", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def criar_relatorio_por_pdfs(
    patient_id: UUID,
    arquivos: list[UploadFile] = File(...),
    observacoes: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Report:
    patient = get_patient_or_404(patient_id, db, current)
    pdfs = ler_pdfs_enviados(arquivos, MAXIMO_DE_ARQUIVOS)

    ai_settings = db.query(AISettings).filter(AISettings.owner_id == current.id).first()
    try:
        provider, model, api_key = resolve_ai_credentials(ai_settings)
        relatorio = generate_report_from_form_pdfs(
            provider=provider,
            model=model,
            api_key=api_key,
            patient_name=patient.name,
            idade=_idade(patient.birth_date) if patient.birth_date else None,
            pdfs=pdfs,
            observacoes=observacoes,
        )
    except AIConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Não foi possível gerar o relatório com o provedor de IA configurado "
                f"({provider}/{model}). Verifique a chave e o modelo em \"Configurações → "
                f"Inteligência Artificial\" (o modelo precisa aceitar PDFs). Detalhe técnico: {exc}"
            ),
        ) from exc

    guardados = guardar_pdfs(patient.id, pdfs)
    template = _template_interno(db, current)
    report = Report(
        patient_id=patient.id,
        template_id=template.id,
        answers_json={"arquivos": guardados, "observacoes": observacoes or ""},
        computed_json={"relatorio": relatorio.model_dump(mode="json")},
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def _laudo_ia_do_psicologo(report_id: UUID, db: Session, current: Psychologist) -> Report:
    report = db.get(Report, report_id)
    if report is None or report.patient.owner_id != current.id or report.template.schema_json.get("rule_type") != RULE_TYPE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relatório não encontrado.")
    return report


class RelatorioIAUpdate(BaseModel):
    relatorio: RelatorioPorPdfs
    # Identificação/capa editáveis na tela de revisão (cidade, data, capa).
    extras: dict | None = None


@router.put("/api/reports/{report_id}/relatorio-ia", response_model=ReportOut)
def salvar_edicoes(
    report_id: UUID,
    data: RelatorioIAUpdate,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Report:
    """Autosave da tela de revisão: o relatório estruturado editado."""
    report = _laudo_ia_do_psicologo(report_id, db, current)
    report.computed_json = {**(report.computed_json or {}), "relatorio": data.relatorio.model_dump(mode="json")}
    if data.extras is not None:
        report.answers_json = {**(report.answers_json or {}), "extras": data.extras}
    db.commit()
    db.refresh(report)
    return report


@router.get("/api/reports/{report_id}/arquivos/{indice}")
def baixar_pdf_original(
    report_id: UUID,
    indice: int,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> Response:
    report = _laudo_ia_do_psicologo(report_id, db, current)
    arquivos = (report.answers_json or {}).get("arquivos", [])
    if not 0 <= indice < len(arquivos):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado.")
    conteudo = get_form_pdfs_storage().read(arquivos[indice]["chave"])
    nome = nome_de_arquivo_seguro(arquivos[indice]["nome"].removesuffix(".pdf"), "pdf")
    return Response(content=conteudo, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{nome}"'})
