import pytest

from app.rules_engine import RulesEngineError, calculate_report

SCHEMA = {
    "name": "Escala De Teste",
    "rule_type": "sum_threshold",
    "areas": [
        {
            "key": "area_1",
            "label": "Área 1",
            "fields": [{"key": "score", "label": "Pontuação", "type": "scale", "min": 0, "max": 4, "weight": 1}],
        },
        {
            "key": "area_2",
            "label": "Área 2",
            "fields": [{"key": "score", "label": "Pontuação", "type": "scale", "min": 0, "max": 4, "weight": 2}],
        },
    ],
    "classification_ranges": [
        {"label": "Baixo", "min": 0, "max": 3},
        {"label": "Médio", "min": 4, "max": 6},
        {"label": "Alto", "min": 7, "max": 12},
    ],
    "chart": {"type": "bar", "group_by": "areas"},
}


def test_calcula_pontuacao_por_area_e_total_respeitando_o_peso():
    answers = {"area_1": {"score": 2}, "area_2": {"score": 1}}

    result = calculate_report(SCHEMA, answers)

    assert result["scores"] == {"area_1": 2.0, "area_2": 2.0}  # area_2: 1 * peso 2
    assert result["total"] == 4.0


@pytest.mark.parametrize(
    "area_1, area_2, esperado",
    [
        (0, 0, "Baixo"),  # total 0, extremo inferior da primeira faixa
        (3, 0, "Baixo"),  # total 3, extremo superior da faixa "Baixo"
        (4, 0, "Médio"),  # total 4, extremo inferior da faixa "Médio" (borda)
        (2, 2, "Médio"),  # total 6, extremo superior da faixa "Médio"
        (4, 2, "Alto"),  # total 8, dentro da faixa "Alto"
        (4, 4, "Alto"),  # total 12, extremo superior da última faixa
    ],
)
def test_classifica_corretamente_em_cada_faixa_incluindo_bordas(area_1, area_2, esperado):
    answers = {"area_1": {"score": area_1}, "area_2": {"score": area_2}}

    result = calculate_report(SCHEMA, answers)

    assert result["classification"] == esperado


def test_total_fora_de_qualquer_faixa_retorna_classificacao_nula():
    schema = {**SCHEMA, "classification_ranges": [{"label": "Único", "min": 100, "max": 200}]}

    result = calculate_report(schema, {"area_1": {"score": 0}, "area_2": {"score": 0}})

    assert result["classification"] is None


def test_falta_resposta_de_uma_area_gera_erro_de_dominio():
    with pytest.raises(RulesEngineError):
        calculate_report(SCHEMA, {"area_1": {"score": 2}})


def test_falta_resposta_de_um_campo_gera_erro_de_dominio():
    with pytest.raises(RulesEngineError):
        calculate_report(SCHEMA, {"area_1": {}, "area_2": {"score": 1}})


def test_resposta_nao_numerica_gera_erro_de_dominio():
    with pytest.raises(RulesEngineError):
        calculate_report(SCHEMA, {"area_1": {"score": "muito"}, "area_2": {"score": 1}})


def test_rule_type_desconhecido_gera_erro_de_dominio():
    schema = {**SCHEMA, "rule_type": "isso_nao_existe"}

    with pytest.raises(RulesEngineError):
        calculate_report(schema, {"area_1": {"score": 0}, "area_2": {"score": 0}})


def test_age_equivalent_percentage_sem_data_de_nascimento_gera_erro_de_dominio():
    schema = {**SCHEMA, "rule_type": "age_equivalent_percentage"}

    with pytest.raises(RulesEngineError):
        calculate_report(schema, {})
