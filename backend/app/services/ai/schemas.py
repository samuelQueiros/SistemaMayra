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


class ConclusionAndInterventions(BaseModel):
    """Saída estruturada da IA para as "Considerações Finais" e as
    "Sugestões De Intervenção" individualizadas de um laudo (pontos 2 e 3
    da revisão de relatórios). Vem em duas seções nomeadas — não um texto
    único — porque o relatório as imprime em blocos separados."""

    consideracoes_finais: str = Field(
        description=(
            "Síntese clínica de fechamento construída a partir do estudo de "
            "caso, das observações clínicas, das habilidades avaliadas, dos "
            "protocolos efetivamente utilizados e da hipótese diagnóstica "
            "selecionada para ESTE paciente — nunca um texto genérico."
        )
    )
    sugestoes_intervencao: str = Field(
        description=(
            "Sugestões de intervenção que decorrem das necessidades, "
            "dificuldades e potencialidades registradas para ESTE paciente — "
            "nunca uma lista fixa associada apenas à hipótese diagnóstica."
        )
    )

    def como_texto_consideracoes(self) -> str:
        return self.consideracoes_finais

    def como_texto_sugestoes(self) -> str:
        return self.sugestoes_intervencao


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


class FormularioLido(BaseModel):
    """Um dos PDFs de respostas (Google Forms) lidos pela IA."""

    arquivo: str = Field(description="Nome do arquivo PDF exatamente como informado.")
    titulo: str = Field(description="Título do formulário, como aparece no PDF.")
    respondente: str | None = Field(
        default=None, description="Quem respondeu e a relação com o paciente (ex.: 'Mãe', 'Professora'), se constar no PDF."
    )
    data: str | None = Field(default=None, description="Data de preenchimento, se constar no PDF (DD/MM/AAAA).")


class GraficoDaArea(BaseModel):
    """Gráfico de barras de uma área, com valores tirados das respostas
    marcadas nos formulários (contagem ou soma — explicada em `regua`)."""

    titulo: str = Field(description="Título curto do gráfico.")
    rotulos: list[str] = Field(description="Rótulo de cada barra (itens, domínios ou respondentes).")
    valores: list[float] = Field(description="Valor de cada barra, na mesma ordem dos rótulos.")
    maximo: float | None = Field(default=None, description="Valor máximo possível da escala, se houver.")
    regua: str = Field(
        description="Uma frase dizendo como os valores foram obtidos (ex.: 'pontos somados: Nunca=0, Às vezes=1, Frequentemente=2, Sempre=3')."
    )


class AreaDoRelatorio(BaseModel):
    titulo: str = Field(description="Área/tema clínico (ex.: 'Comunicação E Linguagem', 'Atenção E Comportamento').")
    texto: str = Field(
        description=(
            "Análise da área em prosa clínica, cruzando o que os diferentes formulários dizem sobre ela "
            "(convergências e divergências entre respondentes). Pode usar **negrito** e linhas começando com • para listas."
        )
    )
    fontes: list[str] = Field(description="Títulos dos formulários de onde vieram os dados desta área.")
    grafico: GraficoDaArea | None = Field(
        default=None,
        description="Só quando houver respostas em escala ou contáveis nesta área. Nunca invente valores.",
    )


class RelatorioPorPdfs(BaseModel):
    """Saída estruturada da IA ao ler os PDFs de respostas dos formulários
    (Google Forms) — vira o relatório no padrão do sistema, organizado por
    área/tema, editável pela psicóloga antes de exportar."""

    formularios: list[FormularioLido] = Field(description="Um item por PDF recebido, na ordem em que foram enviados.")
    metodologia: str = Field(
        description="Parágrafo de metodologia: quais formulários foram aplicados, a quem e com que objetivo, sem inventar instrumentos."
    )
    areas: list[AreaDoRelatorio] = Field(description="Análise organizada por área/tema, cruzando os formulários.")
    consideracoes_finais: str = Field(description="Síntese clínica de fechamento, sem diagnóstico fechado.")
    sugestoes_intervencao: str = Field(
        description="Sugestões de intervenção decorrentes do que foi relatado nos formulários. Linhas começando com • viram lista."
    )


class CampoPreenchido(BaseModel):
    id: str = Field(description="Id exato do campo, copiado do catálogo do protocolo (ex.: 'cars_3', 'parto').")
    valor: str = Field(
        description=(
            "Valor do campo. Em campos com opções, use exatamente o VALOR de uma das opções listadas; "
            "em campos 'marcar', use 'sim' ou 'não'; em campos numéricos, só o número."
        )
    )


class ProtocoloPorIA(BaseModel):
    """Saída estruturada do Laudo Por IA: o estudo de caso e os campos do
    protocolo fixo (formulario-novo-paciente.html) que os PDFs permitem
    preencher. O sistema valida cada campo contra o catálogo e gera o laudo
    padrão (com gráficos) pelo próprio formulário."""

    estudo_de_caso: str = Field(
        description=(
            "Estudo de caso do paciente em prosa clínica, integrando o que os PDFs relatam "
            "(história, queixas, desenvolvimento, comportamento, escola, resultados das escalas)."
        )
    )
    campos: list[CampoPreenchido] = Field(
        description="Campos do catálogo que os PDFs permitem preencher. Omita o que os PDFs não informam."
    )
    lacunas: list[str] = Field(
        default_factory=list,
        description="Informações importantes do protocolo que os PDFs não trazem (para a psicóloga completar).",
    )
