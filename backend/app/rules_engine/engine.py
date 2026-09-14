from datetime import date

from app.rules_engine import age_equivalent_percentage, count_threshold, sum_threshold
from app.rules_engine.exceptions import RulesEngineError


def calculate_report(
    schema: dict,
    answers: dict,
    birth_date: date | None = None,
    evaluation_date: date | None = None,
) -> dict:
    """Aplica o motor de regras do template (SPEC.md seção 4). O formato do
    resultado depende do rule_type: sum_threshold devolve uma classificação
    única ({"scores", "total", "classification"}); count_threshold devolve
    uma classificação por área ({"scores", "classifications"});
    age_equivalent_percentage devolve uma idade de desenvolvimento estimada
    por área ({"areas", "chronological_age_months"})."""

    rule_type = schema.get("rule_type", "sum_threshold")

    if rule_type == "sum_threshold":
        return sum_threshold.calculate(schema, answers)

    if rule_type == "count_threshold":
        return count_threshold.calculate(schema, answers)

    if rule_type == "age_equivalent_percentage":
        if birth_date is None:
            raise RulesEngineError(
                "rule_type 'age_equivalent_percentage' exige a data de nascimento do paciente."
            )
        return age_equivalent_percentage.calculate(
            schema, answers, birth_date, evaluation_date or date.today()
        )

    raise RulesEngineError(f"rule_type desconhecido: '{rule_type}'.")
