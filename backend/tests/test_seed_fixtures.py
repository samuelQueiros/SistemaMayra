import json
from datetime import date
from pathlib import Path

import pytest

from app.rules_engine import calculate_report
from app.schemas.report_template import ReportTemplateSchemaJSON

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "app" / "rules_engine" / "fixtures"


@pytest.mark.parametrize("fixture_name", ["cars.json", "ata.json", "snap_iv.json", "portage.json"])
def test_fixture_e_um_schema_json_valido(fixture_name):
    raw = json.loads((FIXTURES_DIR / fixture_name).read_text(encoding="utf-8"))

    schema = ReportTemplateSchemaJSON.model_validate(raw)

    assert len(schema.areas) > 0
    assert len(schema.classification_ranges) > 0


def test_cars_calcula_classificacao_grave_no_pior_cenario():
    schema = json.loads((FIXTURES_DIR / "cars.json").read_text(encoding="utf-8"))
    answers = {area["key"]: {"score": 4} for area in schema["areas"]}  # pior caso: 4 em tudo

    result = calculate_report(schema, answers)

    assert result["total"] == 60
    assert result["classification"] == "Autismo grave"


def test_cars_calcula_classificacao_normal_no_melhor_cenario():
    schema = json.loads((FIXTURES_DIR / "cars.json").read_text(encoding="utf-8"))
    answers = {area["key"]: {"score": 1} for area in schema["areas"]}  # melhor caso: 1 em tudo

    result = calculate_report(schema, answers)

    assert result["total"] == 15
    assert result["classification"] == "Normal"


def test_snap_iv_calcula_indicativo_de_desatencao_com_4_itens():
    schema = json.loads((FIXTURES_DIR / "snap_iv.json").read_text(encoding="utf-8"))
    respostas_desatencao = {f"item_{i}": "bastante" if i <= 4 else "nem um pouco" for i in range(1, 10)}
    respostas_hiperatividade = {f"item_{i}": "nem um pouco" for i in range(10, 19)}
    answers = {"desatencao": respostas_desatencao, "hiperatividade_impulsividade": respostas_hiperatividade}

    result = calculate_report(schema, answers)

    assert result["scores"]["desatencao"] == 4
    assert result["classifications"]["desatencao"] == "Indicativo de sintomas de desatenção"
    assert result["classifications"]["hiperatividade_impulsividade"] == (
        "Sem indicativo de sintomas de hiperatividade/impulsividade"
    )


def test_portage_calcula_idade_de_desenvolvimento_adequada_no_melhor_cenario():
    schema = json.loads((FIXTURES_DIR / "portage.json").read_text(encoding="utf-8"))
    answers = {
        area["key"]: {
            bracket["label"]: {field["key"]: "sim" for field in bracket["fields"]} for bracket in area["age_brackets"]
        }
        for area in schema["areas"]
    }

    result = calculate_report(schema, answers, birth_date=date(2020, 1, 1), evaluation_date=date(2024, 1, 1))

    for area in schema["areas"]:
        assert result["areas"][area["key"]]["classification"] == "Adequado"
