"""Modelos de laudo (`ReportTemplate`). No fluxo principal só `POST /api/templates/custom-form-avaliacao`
é usado: cria, uma vez por psicóloga, o "porta-laudo" do protocolo fixo. O CRUD e a importação por IA
vieram do motor de regras antigo e continuam disponíveis (ver docs/ARQUITETURA.md)."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import get_current_psychologist
from app.core.database import get_db
from app.models.ai_settings import AISettings
from app.models.psychologist import Psychologist
from app.models.report_template import ReportTemplate
from app.schemas.report_template import (
    ChartConfig,
    ClassificationRange,
    ReportTemplateCreate,
    ReportTemplateOut,
    ReportTemplateSchemaJSON,
    TemplateArea,
    TemplateField,
)
from app.services.ai import AIConfigurationError, extract_template_from_document, resolve_ai_credentials
from app.services.document_text import DocumentTextError, extract_text

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[ReportTemplateOut])
def list_templates(
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> list[ReportTemplate]:
    """Modelos da psicóloga logada."""
    return db.query(ReportTemplate).filter(ReportTemplate.owner_id == current.id).order_by(ReportTemplate.name).all()


@router.post("", response_model=ReportTemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(
    data: ReportTemplateCreate,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> ReportTemplate:
    """Cria um modelo no formato do motor de regras (`schema_json`), já validado pelo schema."""
    template = ReportTemplate(
        owner_id=current.id,
        name=data.name,
        version=data.version,
        schema_json=data.schema_json.model_dump(mode="json"),
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.post("/import")
def import_template_from_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> dict:
    """Extrai, com apoio de IA, um rascunho de `schema_json` a partir de um
    documento (PDF/DOCX/TXT) descrevendo uma escala — para a psicóloga
    revisar/editar antes de cadastrar via `POST /api/templates`. Não
    persiste nada: só devolve o rascunho e os erros de validação, se
    houver, contra o formato estrito (`ReportTemplateSchemaJSON`)."""

    try:
        document_text = extract_text(file)
    except DocumentTextError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not document_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível extrair texto do arquivo enviado.",
        )

    ai_settings = db.query(AISettings).filter(AISettings.owner_id == current.id).first()

    try:
        provider, model, api_key = resolve_ai_credentials(ai_settings)
        draft = extract_template_from_document(
            provider=provider, model=model, api_key=api_key, document_text=document_text
        )
    except AIConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Não foi possível processar o documento com o provedor de IA "
                f"configurado ({provider}/{model}). Verifique a chave de API e o "
                f'modelo em "Configurações". Detalhe técnico: {exc}'
            ),
        ) from exc

    draft_schema_json = {
        "name": draft.name,
        "rule_type": draft.rule_type,
        "areas": [area.model_dump() for area in draft.areas],
        "classification_ranges": [faixa.model_dump() for faixa in draft.classification_ranges],
        "target_values": draft.target_values,
        "item_scoring": draft.item_scoring,
        "chart": {"type": draft.chart_type, "group_by": "areas"},
    }

    validation_errors: list[str] = []
    try:
        ReportTemplateSchemaJSON.model_validate(draft_schema_json)
    except ValidationError as exc:
        validation_errors = [erro["msg"] for erro in exc.errors()]

    return {"draft_schema_json": draft_schema_json, "validation_errors": validation_errors}


_NOME_TEMPLATE_CUSTOM_FORM = "Avaliação Neuropsicopedagógica e Análise Comportamental"


@router.post("/custom-form-avaliacao", response_model=ReportTemplateOut)
def get_or_create_custom_form_template(
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> ReportTemplate:
    """Garante (cria se não existir) o `ReportTemplate` fixo usado pelo
    formulário HTML standalone (`/formulario-novo-paciente.html`) — só serve
    de "porta-laudo" para o rule_type 'custom_form' guardar generated_text/
    pdf; não faz nenhuma pontuação. Idempotente por psicóloga."""
    return garantir_template_custom_form(db, current)


def garantir_template_custom_form(db: Session, current: Psychologist) -> ReportTemplate:
    """Template fixo do protocolo padrão (também usado pelo Laudo Por IA)."""
    existente = (
        db.query(ReportTemplate)
        .filter(ReportTemplate.owner_id == current.id, ReportTemplate.name == _NOME_TEMPLATE_CUSTOM_FORM)
        .first()
    )
    if existente:
        return existente

    schema_json = ReportTemplateSchemaJSON(
        name=_NOME_TEMPLATE_CUSTOM_FORM,
        rule_type="custom_form",
        areas=[
            TemplateArea(
                key="formulario",
                label="Formulário Completo",
                fields=[TemplateField(key="html", label="HTML", type="text")],
            )
        ],
        classification_ranges=[ClassificationRange(label="Não Aplicável (Formulário Externo)", min=0, max=0)],
        chart=ChartConfig(type="bar", group_by="areas"),
    )
    template = ReportTemplate(
        owner_id=current.id,
        name=schema_json.name,
        version=1,
        schema_json=schema_json.model_dump(mode="json"),
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/{template_id}", response_model=ReportTemplateOut)
def get_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current: Psychologist = Depends(get_current_psychologist),
) -> ReportTemplate:
    """Um modelo da psicóloga logada (404 se for de outra conta)."""
    template = db.get(ReportTemplate, template_id)
    if template is None or template.owner_id != current.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo não encontrado")
    return template
