from datetime import date

import pytest

from app.rules_engine import RulesEngineError, calculate_report

# Idade cronológica de referência nos testes: paciente nasceu em 2020-01-01,
# avaliado em 2024-01-01 -> exatamente 48 meses (4 anos).
NASCIMENTO = date(2020, 1, 1)
AVALIACAO = date(2024, 1, 1)

SCHEMA = {
    "name": "Inventário Portage Operacionalizado (IPO) — teste",
    "rule_type": "age_equivalent_percentage",
    "item_scoring": {"sim": 1.0, "as_vezes": 0.5, "nao": 0.2},
    "areas": [
        {
            "key": "socializacao",
            "label": "Socialização",
            "age_brackets": [
                {
                    "label": "0-24 meses",
                    "max_age_months": 24,
                    "fields": [
                        {"key": "item_1", "label": "Item 1", "type": "select", "options": ["sim", "as_vezes", "nao"]},
                        {"key": "item_2", "label": "Item 2", "type": "select", "options": ["sim", "as_vezes", "nao"]},
                    ],
                },
                {
                    "label": "24-48 meses",
                    "max_age_months": 48,
                    "fields": [
                        {"key": "item_3", "label": "Item 3", "type": "select", "options": ["sim", "as_vezes", "nao"]},
                        {"key": "item_4", "label": "Item 4", "type": "select", "options": ["sim", "as_vezes", "nao"]},
                    ],
                },
            ],
        }
    ],
    "classification_ranges": [
        {"label": "Atraso significativo", "min": 0, "max": 69.9},
        {"label": "Atraso leve", "min": 70, "max": 89.9},
        {"label": "Adequado", "min": 90, "max": 200},
    ],
    "chart": {"type": "bar", "group_by": "areas", "compare_to": "idade_cronologica"},
}


def _answers(faixa_1: dict, faixa_2: dict) -> dict:
    return {"socializacao": {"0-24 meses": faixa_1, "24-48 meses": faixa_2}}


def test_todas_as_faixas_atingidas_da_idade_maxima_cadastrada():
    answers = _answers(
        {"item_1": "sim", "item_2": "sim"},
        {"item_3": "sim", "item_4": "sim"},
    )

    result = calculate_report(SCHEMA, answers, birth_date=NASCIMENTO, evaluation_date=AVALIACAO)

    area = result["areas"]["socializacao"]
    assert area["developmental_age_months"] == 48.0
    assert area["percentage"] == 100.0
    assert area["classification"] == "Adequado"
    assert result["chronological_age_months"] == 48


def test_credito_parcial_interpolado_na_faixa_nao_atingida():
    # Primeira faixa 100% atingida (24 meses), segunda faixa pela metade
    # (item_3 sim, item_4 não) -> ratio 0.6 (1.0 + 0.2) / 2 = 0.6, abaixo do
    # limiar de 0.75, então soma parcial: 24 + (48-24)*0.6 = 38.4 meses.
    answers = _answers(
        {"item_1": "sim", "item_2": "sim"},
        {"item_3": "sim", "item_4": "nao"},
    )

    result = calculate_report(SCHEMA, answers, birth_date=NASCIMENTO, evaluation_date=AVALIACAO)

    area = result["areas"]["socializacao"]
    assert area["developmental_age_months"] == 38.4
    assert area["percentage"] == 80.0
    assert area["classification"] == "Atraso leve"


def test_primeira_faixa_nao_atingida_gera_credito_parcial_desde_zero():
    # ratio da primeira faixa: (0.5 + 0.2)/2 = 0.35 -> dev = 0 + 24*0.35 = 8.4
    answers = _answers(
        {"item_1": "as_vezes", "item_2": "nao"},
        {"item_3": "sim", "item_4": "sim"},
    )

    result = calculate_report(SCHEMA, answers, birth_date=NASCIMENTO, evaluation_date=AVALIACAO)

    area = result["areas"]["socializacao"]
    assert area["developmental_age_months"] == 8.4
    assert area["classification"] == "Atraso significativo"


def test_classificacao_muda_conforme_idade_cronologica_cresce_e_desenvolvimento_fica_para_tras():
    # Desenvolvimento atinge o máximo cadastrado (48 meses) mas a idade
    # cronológica já é maior (67 meses) -> percentual cai para a faixa
    # "Atraso leve" mesmo com todos os itens marcados "sim".
    answers = _answers(
        {"item_1": "sim", "item_2": "sim"},
        {"item_3": "sim", "item_4": "sim"},
    )
    avaliacao_com_idade_maior = date(2025, 8, 1)  # 67 meses cronológicos

    result = calculate_report(SCHEMA, answers, birth_date=NASCIMENTO, evaluation_date=avaliacao_com_idade_maior)

    area = result["areas"]["socializacao"]
    assert result["chronological_age_months"] == 67
    assert area["percentage"] == 71.6
    assert area["classification"] == "Atraso leve"


def test_faixas_fora_de_ordem_no_schema_sao_ordenadas_pelo_motor():
    schema_desordenado = {
        **SCHEMA,
        "areas": [
            {
                **SCHEMA["areas"][0],
                "age_brackets": list(reversed(SCHEMA["areas"][0]["age_brackets"])),
            }
        ],
    }
    answers = _answers(
        {"item_1": "sim", "item_2": "sim"},
        {"item_3": "sim", "item_4": "sim"},
    )

    result = calculate_report(schema_desordenado, answers, birth_date=NASCIMENTO, evaluation_date=AVALIACAO)

    assert result["areas"]["socializacao"]["developmental_age_months"] == 48.0


def test_sem_data_de_nascimento_gera_erro_de_dominio():
    answers = _answers({"item_1": "sim", "item_2": "sim"}, {"item_3": "sim", "item_4": "sim"})

    with pytest.raises(RulesEngineError):
        calculate_report(SCHEMA, answers)


def test_data_de_nascimento_posterior_a_avaliacao_gera_erro_de_dominio():
    answers = _answers({"item_1": "sim", "item_2": "sim"}, {"item_3": "sim", "item_4": "sim"})

    with pytest.raises(RulesEngineError):
        calculate_report(SCHEMA, answers, birth_date=date(2030, 1, 1), evaluation_date=AVALIACAO)


def test_falta_resposta_de_uma_faixa_gera_erro_de_dominio():
    answers = {"socializacao": {"0-24 meses": {"item_1": "sim", "item_2": "sim"}}}

    with pytest.raises(RulesEngineError):
        calculate_report(SCHEMA, answers, birth_date=NASCIMENTO, evaluation_date=AVALIACAO)


def test_resposta_invalida_gera_erro_de_dominio():
    answers = _answers(
        {"item_1": "sim", "item_2": "talvez"},
        {"item_3": "sim", "item_4": "sim"},
    )

    with pytest.raises(RulesEngineError):
        calculate_report(SCHEMA, answers, birth_date=NASCIMENTO, evaluation_date=AVALIACAO)


def test_schema_sem_item_scoring_gera_erro_de_dominio():
    schema = {**SCHEMA, "item_scoring": {}}
    answers = _answers({"item_1": "sim", "item_2": "sim"}, {"item_3": "sim", "item_4": "sim"})

    with pytest.raises(RulesEngineError):
        calculate_report(schema, answers, birth_date=NASCIMENTO, evaluation_date=AVALIACAO)
