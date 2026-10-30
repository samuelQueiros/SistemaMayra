"""Cálculo "contagem por área": conta, em cada área, os itens que batem com `target_values` (ex.: SNAP-IV) e
classifica cada área pelas faixas do modelo."""

from app.rules_engine.exceptions import RulesEngineError

_COMPARADORES = {
    "gte": lambda contagem, minimo: contagem >= minimo,
    "gt": lambda contagem, minimo: contagem > minimo,
    "lte": lambda contagem, minimo: contagem <= minimo,
    "lt": lambda contagem, minimo: contagem < minimo,
    "eq": lambda contagem, minimo: contagem == minimo,
}


def calculate(schema: dict, answers: dict) -> dict:
    """Conta, por área, quantos campos bateram em um dos `target_values`
    (ex.: "bastante"/"demais" no SNAP-IV, ver TEMPLATES_LAUDOS.md seção 4)
    e classifica cada área separadamente contra `classification_ranges`."""

    target_values = set(schema.get("target_values", []))
    if not target_values:
        raise RulesEngineError("rule_type 'count_threshold' exige 'target_values' no schema_json.")

    scores: dict[str, int] = {}
    for area in schema["areas"]:
        area_key = area["key"]
        area_answers = answers.get(area_key)
        if area_answers is None:
            raise RulesEngineError(f"Faltam respostas para a área '{area_key}'.")

        count = 0
        for field in area["fields"]:
            field_key = field["key"]
            if field_key not in area_answers:
                raise RulesEngineError(f"Falta a resposta do campo '{field_key}' na área '{area_key}'.")
            if area_answers[field_key] in target_values:
                count += 1
        scores[area_key] = count

    classifications = {
        area["key"]: _classificar_area(schema["classification_ranges"], area["key"], scores[area["key"]])
        for area in schema["areas"]
    }

    return {"scores": scores, "classifications": classifications}


def _classificar_area(classification_ranges: list[dict], area_key: str, count: int) -> str | None:
    for faixa in classification_ranges:
        if faixa.get("area") != area_key:
            continue
        comparador = _COMPARADORES.get(faixa.get("comparison"))
        if comparador is None:
            raise RulesEngineError(
                f"Faixa da área '{area_key}' tem 'comparison' inválido ou ausente: {faixa.get('comparison')!r}."
            )
        if comparador(count, faixa["minimum_count"]):
            return faixa["label"]
    return None
