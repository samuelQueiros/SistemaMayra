from app.rules_engine.exceptions import RulesEngineError

# `answers` é organizado por área para evitar colisão de chaves: templates
# reais (ex.: CARS, ver TEMPLATES_LAUDOS.md seção 2) repetem a mesma chave
# de campo ("score") em todas as áreas, então uma resposta plana por
# `field.key` (como no pseudocódigo simplificado do SPEC.md seção 4) causaria
# um valor sobrescrever o outro. Formato esperado:
# {"area_key": {"field_key": valor, ...}, ...}


def calculate(schema: dict, answers: dict) -> dict:
    scores: dict[str, float] = {}

    for area in schema["areas"]:
        area_key = area["key"]
        area_answers = answers.get(area_key)
        if area_answers is None:
            raise RulesEngineError(f"Faltam respostas para a área '{area_key}'.")

        area_total = 0.0
        for field in area["fields"]:
            field_key = field["key"]
            if field_key not in area_answers:
                raise RulesEngineError(f"Falta a resposta do campo '{field_key}' na área '{area_key}'.")
            value = _valor_numerico(area_key, field, area_answers[field_key])
            area_total += value * field.get("weight", 1)

        scores[area_key] = area_total

    total = sum(scores.values())
    classification = _classificar(schema["classification_ranges"], total)

    return {"scores": scores, "total": total, "classification": classification}


def _valor_numerico(area_key: str, field: dict, raw_value) -> float:
    if isinstance(raw_value, bool):
        return 1.0 if raw_value else 0.0
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    raise RulesEngineError(
        f"Resposta inválida para o campo '{field['key']}' na área '{area_key}': "
        f"esperado um número, recebido {raw_value!r}."
    )


def _classificar(classification_ranges: list[dict], total: float) -> str | None:
    for faixa in classification_ranges:
        if faixa["min"] <= total <= faixa["max"]:
            return faixa["label"]
    return None
