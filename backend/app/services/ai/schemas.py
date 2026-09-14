from pydantic import BaseModel, Field


class ExtractedTemplateField(BaseModel):
    """Um item/pergunta dentro de uma área, extraído do documento da
    escala. Mais permissivo que `TemplateField` (schemas/report_template.py)
    de propósito — sem validação cruzada por tipo — para não travar a
    geração estruturada da IA; a psicóloga revisa antes de salvar."""

    key: str = Field(description="Chave técnica do campo, em snake_case, sem espaços ou acentos.")
    label: str = Field(description="Rótulo legível do campo/item, em português.")
    type: str = Field(description="Um de: 'scale' (numérico), 'boolean' (sim/não), 'select' (opções fixas), 'text'.")
    min: float | None = Field(default=None, description="Valor mínimo, só quando type='scale'.")
    max: float | None = Field(default=None, description="Valor máximo, só quando type='scale'.")
    options: list[str] | None = Field(default=None, description="Opções fixas, só quando type='select'.")
    weight: float = Field(default=1, description="Peso do campo na soma total (rule_type 'sum_threshold').")


class ExtractedTemplateArea(BaseModel):
    key: str = Field(description="Chave técnica da área/domínio, em snake_case.")
    label: str = Field(description="Rótulo legível da área/domínio avaliado.")
    fields: list[ExtractedTemplateField] = Field(default_factory=list)


class ExtractedClassificationRange(BaseModel):
    label: str = Field(description="Nome da classificação (ex.: 'Normal', 'Grave').")
    min: float | None = Field(default=None, description="Mínimo da faixa (rule_type 'sum_threshold').")
    max: float | None = Field(default=None, description="Máximo da faixa (rule_type 'sum_threshold').")
    area: str | None = Field(default=None, description="Área a que a faixa se refere (rule_type 'count_threshold').")
    minimum_count: int | None = Field(default=None, description="Quantidade mínima exigida (rule_type 'count_threshold').")
    comparison: str | None = Field(
        default=None, description="Comparação usada com minimum_count: gte, gt, lte, lt ou eq."
    )


class ExtractedTemplateDraft(BaseModel):
    """Rascunho de `schema_json` (ver schemas/report_template.py) extraído
    por IA a partir do texto de um documento de escala enviado pela
    psicóloga. Deliberadamente mais permissivo que `ReportTemplateSchemaJSON`
    — sem os `model_validator` cruzados dele — porque a extração estruturada
    da IA pode não acertar tudo de primeira; o rascunho é sempre revisado/
    editado pela psicóloga antes de virar um `ReportTemplate` de verdade
    (via POST /api/templates, que usa o schema estrito)."""

    name: str = Field(description="Nome da escala/instrumento, ex.: 'Escala CARS'.")
    rule_type: str = Field(
        default="sum_threshold",
        description=(
            "Tipo de regra de pontuação mais adequado ao documento: "
            "'sum_threshold' (soma pontos e compara com faixas), "
            "'count_threshold' (conta itens que bateram em valores específicos), "
            "ou 'age_equivalent_percentage' (compara habilidades com a idade cronológica)."
        ),
    )
    areas: list[ExtractedTemplateArea] = Field(default_factory=list)
    classification_ranges: list[ExtractedClassificationRange] = Field(default_factory=list)
    target_values: list[str] | None = Field(
        default=None, description="Só para rule_type 'count_threshold': valores que contam (ex.: ['bastante', 'demais'])."
    )
    item_scoring: dict[str, float] | None = Field(
        default=None,
        description="Só para rule_type 'age_equivalent_percentage': peso numérico de cada resposta possível.",
    )
    chart_type: str = Field(default="bar", description="Tipo de gráfico mais adequado: 'bar', 'radar' ou 'pie'.")


class ReportSections(BaseModel):
    """Saída estruturada da IA para o texto descritivo do laudo (SPEC.md
    seção 5). Seções nomeadas em vez de um texto único solto, para casar
    com o layout do laudo e não depender do formato livre do modelo."""

    introducao: str = Field(description="Parágrafo introdutório contextualizando a avaliação e o motivo do atendimento.")
    analise_por_area: str = Field(
        description="Análise descritiva dos resultados por área/domínio avaliado, com base nas pontuações e classificação calculadas."
    )
    conclusao: str = Field(
        description="Conclusão do parecer e recomendações gerais, sem propor diagnóstico fechado nem inventar dados não informados."
    )

    def como_texto(self) -> str:
        return (
            f"{self.introducao}\n\n"
            f"{self.analise_por_area}\n\n"
            f"{self.conclusao}"
        )
