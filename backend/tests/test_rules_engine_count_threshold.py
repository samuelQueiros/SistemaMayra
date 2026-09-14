import pytest

from app.rules_engine import RulesEngineError, calculate_report

NIVEIS = ["nem um pouco", "só um pouco", "bastante", "demais"]


def _area_com_9_itens(key: str, label: str) -> dict:
    return {
        "key": key,
        "label": label,
        "fields": [
            {
                "key": f"item_{i}",
                "label": f"Item {i}",
                "type": "select",
                "options": NIVEIS,
                "weight": 1,
            }
            for i in range(1, 10)
        ],
    }


SCHEMA = {
    "name": "SNAP-IV De Teste",
    "rule_type": "count_threshold",
    "target_values": ["bastante", "demais"],
    "areas": [
        _area_com_9_itens("desatencao", "Desatenção"),
        _area_com_9_itens("hiperatividade_impulsividade", "Hiperatividade / Impulsividade"),
    ],
    "classification_ranges": [
        {"area": "desatencao", "minimum_count": 4, "comparison": "gte", "label": "Indicativo de desatenção"},
        {"area": "desatencao", "minimum_count": 4, "comparison": "lt", "label": "Sem indicativo de desatenção"},
        {
            "area": "hiperatividade_impulsividade",
            "minimum_count": 4,
            "comparison": "gte",
            "label": "Indicativo de hiperatividade",
        },
        {
            "area": "hiperatividade_impulsividade",
            "minimum_count": 4,
            "comparison": "lt",
            "label": "Sem indicativo de hiperatividade",
        },
    ],
    "chart": {"type": "bar", "group_by": "response_option"},
}


def _respostas(area_key: str, quantidade_bastante_ou_demais: int) -> dict:
    """Monta as 9 respostas de uma área: as N primeiras em "bastante" (contam
    para o limite) e o resto em "nem um pouco" (não contam)."""
    respostas = {}
    for i in range(1, 10):
        respostas[f"item_{i}"] = "bastante" if i <= quantidade_bastante_ou_demais else "nem um pouco"
    return {area_key: respostas}


def test_conta_quantos_itens_bateram_em_bastante_ou_demais():
    answers = {
        **_respostas("desatencao", 3),
        **_respostas("hiperatividade_impulsividade", 4),
    }

    result = calculate_report(SCHEMA, answers)

    assert result["scores"] == {"desatencao": 3, "hiperatividade_impulsividade": 4}


def test_exatamente_4_itens_em_bastante_ou_demais_e_classificado_como_indicativo():
    answers = {
        **_respostas("desatencao", 4),
        **_respostas("hiperatividade_impulsividade", 0),
    }

    result = calculate_report(SCHEMA, answers)

    assert result["classifications"]["desatencao"] == "Indicativo de desatenção"


def test_3_itens_em_bastante_ou_demais_e_classificado_como_nao_indicativo():
    answers = {
        **_respostas("desatencao", 3),
        **_respostas("hiperatividade_impulsividade", 0),
    }

    result = calculate_report(SCHEMA, answers)

    assert result["classifications"]["desatencao"] == "Sem indicativo de desatenção"


def test_areas_sao_classificadas_de_forma_independente():
    answers = {
        **_respostas("desatencao", 8),
        **_respostas("hiperatividade_impulsividade", 1),
    }

    result = calculate_report(SCHEMA, answers)

    assert result["classifications"]["desatencao"] == "Indicativo de desatenção"
    assert result["classifications"]["hiperatividade_impulsividade"] == "Sem indicativo de hiperatividade"


def test_demais_tambem_conta_para_o_limite_junto_com_bastante():
    respostas_desatencao = {f"item_{i}": "nem um pouco" for i in range(1, 10)}
    respostas_desatencao["item_1"] = "demais"
    respostas_desatencao["item_2"] = "bastante"
    respostas_desatencao["item_3"] = "demais"
    respostas_desatencao["item_4"] = "bastante"
    answers = {
        "desatencao": respostas_desatencao,
        **_respostas("hiperatividade_impulsividade", 0),
    }

    result = calculate_report(SCHEMA, answers)

    assert result["scores"]["desatencao"] == 4
    assert result["classifications"]["desatencao"] == "Indicativo de desatenção"


def test_schema_sem_target_values_gera_erro_de_dominio():
    schema = {**SCHEMA, "target_values": []}

    with pytest.raises(RulesEngineError):
        calculate_report(schema, {**_respostas("desatencao", 0), **_respostas("hiperatividade_impulsividade", 0)})
