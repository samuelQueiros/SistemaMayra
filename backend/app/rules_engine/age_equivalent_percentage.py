from datetime import date

from app.rules_engine.exceptions import RulesEngineError

# Diferente de sum_threshold/count_threshold, aqui cada área é organizada em
# faixas etárias (`age_brackets`), não em campos soltos — porque o cálculo
# do Portage/IPO não é "somar e comparar contra uma faixa", é estimar uma
# "idade de desenvolvimento" por área a partir de quais faixas a criança já
# domina. Formato esperado de `answers`:
# {"area_key": {"faixa_label": {"field_key": "sim"|"as_vezes"|"nao", ...}, ...}, ...}

_LIMIAR_FAIXA_ATINGIDA = 0.75


def calculate(schema: dict, answers: dict, birth_date: date, evaluation_date: date) -> dict:
    """Estima, por área, uma idade de desenvolvimento a partir de faixas
    etárias de habilidades cadastradas pela psicóloga (ver
    TEMPLATES_LAUDOS.md seção 5). O inventário oficial do Portage (~580
    itens com idade mapeada individualmente) ainda não foi fornecido pela
    clínica — em vez de bloquear a escala inteira por isso, a psicóloga
    organiza os itens que já tem em faixas etárias por área ao cadastrar o
    template, e o motor interpola a idade de desenvolvimento a partir de
    quantas faixas foram atingidas."""

    item_scoring = schema.get("item_scoring")
    if not item_scoring:
        raise RulesEngineError(
            "rule_type 'age_equivalent_percentage' exige 'item_scoring' no schema_json."
        )

    chronological_months = _meses_entre(birth_date, evaluation_date)
    if chronological_months <= 0:
        raise RulesEngineError(
            "Data de nascimento do paciente é inválida para o cálculo de idade "
            "(deve ser anterior à data da avaliação)."
        )

    areas_resultado: dict[str, dict] = {}
    for area in schema["areas"]:
        area_key = area["key"]
        area_answers = answers.get(area_key)
        if area_answers is None:
            raise RulesEngineError(f"Faltam respostas para a área '{area_key}'.")

        brackets = area.get("age_brackets")
        if not brackets:
            raise RulesEngineError(f"Área '{area_key}' não tem faixas etárias (age_brackets).")

        developmental_months = _idade_de_desenvolvimento(
            area_key, sorted(brackets, key=lambda b: b["max_age_months"]), area_answers, item_scoring
        )
        percentage = (developmental_months / chronological_months) * 100
        classification = _classificar(schema["classification_ranges"], percentage)

        areas_resultado[area_key] = {
            "developmental_age_months": round(developmental_months, 1),
            "developmental_age_label": _formatar_idade(developmental_months),
            "percentage": round(percentage, 1),
            "classification": classification,
        }

    return {"areas": areas_resultado, "chronological_age_months": chronological_months}


def _idade_de_desenvolvimento(
    area_key: str, brackets: list[dict], area_answers: dict, item_scoring: dict
) -> float:
    developmental_months = 0.0
    previous_limit = 0.0

    for bracket in brackets:
        bracket_label = bracket["label"]
        bracket_answers = area_answers.get(bracket_label)
        if bracket_answers is None:
            raise RulesEngineError(
                f"Faltam respostas da faixa '{bracket_label}' na área '{area_key}'."
            )

        limit = float(bracket["max_age_months"])
        ratio = _razao_atingida(area_key, bracket_label, bracket["fields"], bracket_answers, item_scoring)

        if ratio >= _LIMIAR_FAIXA_ATINGIDA:
            developmental_months = limit
            previous_limit = limit
            continue

        developmental_months = previous_limit + (limit - previous_limit) * ratio
        break

    return developmental_months


def _razao_atingida(
    area_key: str, bracket_label: str, fields: list[dict], bracket_answers: dict, item_scoring: dict
) -> float:
    total = 0.0
    for field in fields:
        field_key = field["key"]
        if field_key not in bracket_answers:
            raise RulesEngineError(
                f"Falta a resposta do item '{field_key}' na faixa '{bracket_label}' "
                f"da área '{area_key}'."
            )
        resposta = bracket_answers[field_key]
        if resposta not in item_scoring:
            raise RulesEngineError(
                f"Resposta inválida '{resposta}' no item '{field_key}' (faixa "
                f"'{bracket_label}', área '{area_key}'): esperado uma das chaves de "
                f"'item_scoring' ({sorted(item_scoring)})."
            )
        total += item_scoring[resposta]
    return total / len(fields)


def _meses_entre(inicio: date, fim: date) -> int:
    meses = (fim.year - inicio.year) * 12 + (fim.month - inicio.month)
    if fim.day < inicio.day:
        meses -= 1
    return meses


def _formatar_idade(months: float) -> str:
    anos, meses = divmod(round(months), 12)
    partes = []
    if anos:
        partes.append(f"{anos} ano{'s' if anos != 1 else ''}")
    if meses or not anos:
        partes.append(f"{meses} mês{'es' if meses != 1 else ''}")
    return " e ".join(partes)


def _classificar(classification_ranges: list[dict], percentage: float) -> str | None:
    for faixa in classification_ranges:
        if faixa["min"] <= percentage <= faixa["max"]:
            return faixa["label"]
    return None
