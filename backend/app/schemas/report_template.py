from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

FieldType = Literal["scale", "boolean", "select", "text"]
ChartType = Literal["bar", "radar", "pie"]
RuleType = Literal["sum_threshold", "count_threshold", "age_equivalent_percentage"]


class TemplateField(BaseModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    type: FieldType
    min: float | None = None
    max: float | None = None
    options: list[str] | None = None
    weight: float = 1

    @model_validator(mode="after")
    def validar_por_tipo(self) -> "TemplateField":
        if self.type == "scale":
            if self.min is None or self.max is None:
                raise ValueError(f"Campo '{self.key}': tipo 'scale' exige 'min' e 'max'.")
            if self.max <= self.min:
                raise ValueError(f"Campo '{self.key}': 'max' deve ser maior que 'min'.")
        if self.type == "select" and not self.options:
            raise ValueError(f"Campo '{self.key}': tipo 'select' exige 'options' não vazio.")
        return self


class AgeBracket(BaseModel):
    """Faixa etária de uma área no formato "age_equivalent_percentage"
    (Portage/IPO — ver TEMPLATES_LAUDOS.md seção 5). Em vez de depender do
    inventário oficial completo (~580 habilidades com idade mapeada uma a
    uma, que a clínica ainda não forneceu), a psicóloga organiza os itens
    que já tem em faixas etárias por área; o motor de regras estima a
    "idade de desenvolvimento" por interpolação entre faixas atingidas."""

    label: str = Field(min_length=1)
    max_age_months: int = Field(gt=0)
    fields: list[TemplateField] = Field(min_length=1)


class TemplateArea(BaseModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    # Áreas no formato "sum_threshold"/"count_threshold" (SPEC.md seção 3).
    fields: list[TemplateField] | None = None
    # Áreas no formato "age_equivalent_percentage" (Portage/IPO).
    age_brackets: list[AgeBracket] | None = None

    @model_validator(mode="after")
    def exige_fields_ou_age_brackets(self) -> "TemplateArea":
        if not self.fields and not self.age_brackets:
            raise ValueError(
                f"Área '{self.key}': informe 'fields' (escalas comuns) ou "
                "'age_brackets' (formato age_equivalent_percentage)."
            )
        return self


ComparisonOperator = Literal["gte", "gt", "lte", "lt", "eq"]


class ClassificationRange(BaseModel):
    label: str = Field(min_length=1)
    # sum_threshold (SPEC.md seção 3): faixa numérica sobre o total.
    min: float | None = None
    max: float | None = None
    # count_threshold (TEMPLATES_LAUDOS.md seção 4): classifica uma área
    # específica comparando a contagem de itens contra um mínimo.
    area: str | None = None
    minimum_count: int | None = None
    comparison: ComparisonOperator | None = None


class ChartConfig(BaseModel):
    type: ChartType
    group_by: str = "areas"
    compare_to: str | None = None


class ReportTemplateSchemaJSON(BaseModel):
    """Formato de `schema_json` de um `ReportTemplate` — ver SPEC.md seção 3
    e TEMPLATES_LAUDOS.md para os exemplos reais (CARS, ATA, SNAP-IV)."""

    name: str = Field(min_length=1)
    rule_type: RuleType = "sum_threshold"
    areas: list[TemplateArea] = Field(min_length=1)
    classification_ranges: list[ClassificationRange] = Field(min_length=1)
    chart: ChartConfig
    # Só usado quando rule_type == "count_threshold" (ex.: SNAP-IV conta
    # quantos itens de uma área caem em "bastante" ou "demais" — ver
    # TEMPLATES_LAUDOS.md seção 4).
    target_values: list[str] | None = None
    # Só usado quando rule_type == "age_equivalent_percentage": como cada
    # resposta de item vira um valor numérico (ex.: {"sim": 1.0,
    # "as_vezes": 0.5, "nao": 0.2} — TEMPLATES_LAUDOS.md seção 5).
    item_scoring: dict[str, float] | None = None

    @model_validator(mode="after")
    def validar_faixas_de_acordo_com_o_rule_type(self) -> "ReportTemplateSchemaJSON":
        if self.rule_type == "sum_threshold":
            for faixa in self.classification_ranges:
                if faixa.min is None or faixa.max is None:
                    raise ValueError(
                        f"Faixa '{faixa.label}': rule_type 'sum_threshold' exige "
                        "'min' e 'max' em classification_ranges."
                    )
                if faixa.max <= faixa.min:
                    raise ValueError(f"Faixa '{faixa.label}': 'max' deve ser maior que 'min'.")

        if self.rule_type == "count_threshold":
            if not self.target_values:
                raise ValueError("rule_type 'count_threshold' exige 'target_values' não vazio.")
            chaves_de_area = {area.key for area in self.areas}
            for faixa in self.classification_ranges:
                if faixa.area is None or faixa.minimum_count is None or faixa.comparison is None:
                    raise ValueError(
                        f"Faixa '{faixa.label}': rule_type 'count_threshold' exige 'area', "
                        "'minimum_count' e 'comparison' em classification_ranges."
                    )
                if faixa.area not in chaves_de_area:
                    raise ValueError(
                        f"Faixa '{faixa.label}': área '{faixa.area}' não existe em 'areas'."
                    )

        if self.rule_type == "age_equivalent_percentage":
            if not self.item_scoring:
                raise ValueError(
                    "rule_type 'age_equivalent_percentage' exige 'item_scoring' não vazio."
                )
            for area in self.areas:
                if not area.age_brackets:
                    raise ValueError(
                        f"Área '{area.key}': rule_type 'age_equivalent_percentage' exige "
                        "'age_brackets'."
                    )
            for faixa in self.classification_ranges:
                if faixa.min is None or faixa.max is None:
                    raise ValueError(
                        f"Faixa '{faixa.label}': rule_type 'age_equivalent_percentage' exige "
                        "'min' e 'max' em classification_ranges (percentual da idade "
                        "cronológica)."
                    )
                if faixa.max <= faixa.min:
                    raise ValueError(f"Faixa '{faixa.label}': 'max' deve ser maior que 'min'.")
        return self


class ReportTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    version: int = 1
    schema_json: ReportTemplateSchemaJSON


class ReportTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: int
    schema_json: dict
