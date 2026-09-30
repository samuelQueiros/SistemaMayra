from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReportCreate(BaseModel):
    template_id: UUID
    answers: dict
    # Só relevante para rule_type "age_equivalent_percentage" (Portage/IPO),
    # que precisa da idade do paciente na data da avaliação. Default: hoje.
    evaluation_date: date | None = None


class ReportTextUpdate(BaseModel):
    generated_text: str


class ConclusionRequest(BaseModel):
    """Dados curados de UM paciente (já filtrados/selecionados pelo
    formulário), enviados à IA para compor as Considerações Finais e as
    Sugestões De Intervenção — pontos 2 e 3 da revisão de relatórios. Cada
    campo é o resumo textual já pronto (o formulário standalone monta esse
    resumo a partir do que a psicóloga preencheu; nada aqui é recalculado
    no backend)."""

    patient_name: str
    estudo_de_caso: str | None = None
    observacoes_clinicas: str | None = None
    habilidades_avaliadas: str | None = None
    protocolos_utilizados: str | None = None
    hipotese_selecionada: str | None = None


class ConclusionResponse(BaseModel):
    consideracoes_finais: str
    sugestoes_intervencao: str


class ReportAnswersUpdate(BaseModel):
    """Autosave das respostas de um laudo em edição (ver formulário
    standalone `formulario-novo-paciente.html`): cada campo alterado
    sincroniza com o banco, substituindo integralmente `answers_json`."""

    answers: dict


class ReportEditUpdate(BaseModel):
    """Correção manual do que aparece no histórico. Só os campos enviados
    são alterados (ver `exclude_unset` no endpoint) — cada mudança de
    valor vira uma entrada em ReportChangeLog."""

    template_name_override: str | None = None
    classification_override: str | None = None


class DiagnosticHypothesis(BaseModel):
    label: str
    cid: str | None = None
    # Só a hipótese com selected=True aparece no PDF (nunca a lista
    # completa das hipóteses investigadas) — ver `_secoes_clinicas_html`.
    selected: bool = False


class ClinicalSections(BaseModel):
    """Seções clínicas opcionais do PDF completo (ver ENTREGAS.md —
    "PDF completo"). Cada campo ausente/None é simplesmente omitido no PDF,
    preservando a compatibilidade com laudos antigos gerados antes dessa
    funcionalidade."""

    anamnese: str | None = None
    historico_desenvolvimento: str | None = None
    encaminhamento_queixas: str | None = None
    metodologia: str | None = None
    estudo_de_caso: str | None = None
    plano_intervencao: str | None = None
    encaminhamentos: list[str] | None = None
    consideracoes_finais: str | None = None
    diagnostic_hypotheses: list[DiagnosticHypothesis] | None = None


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    template_id: UUID
    answers_json: dict
    computed_json: dict | None = None
    generated_text: str | None = None
    pdf_path: str | None = None
    template_name_override: str | None = None
    classification_override: str | None = None
    clinical_sections_json: dict | None = None
    created_at: datetime


class ReportChangeLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    field: str
    old_value: str | None
    new_value: str | None
    created_at: datetime
    psychologist_name: str


class ConsolidatedPdfRequest(BaseModel):
    report_ids: list[UUID]


class ConsolidatedReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: UUID
    report_ids: list[str]
    generated_text: str
    created_at: datetime
