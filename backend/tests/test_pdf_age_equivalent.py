from app.services.pdf import _cabecalho_tabela_pontuacao, _gerar_grafico, _linhas_pontuacao

SCHEMA = {
    "name": "Portage De Teste",
    "areas": [
        {"key": "socializacao", "label": "Socialização"},
        {"key": "linguagem", "label": "Linguagem"},
    ],
    "chart": {"type": "bar"},
}

COMPUTED = {
    "areas": {
        "socializacao": {
            "developmental_age_months": 38.4,
            "developmental_age_label": "3 anos e 2 meses",
            "percentage": 80.0,
            "classification": "Atraso leve",
        },
        "linguagem": {
            "developmental_age_months": 48.0,
            "developmental_age_label": "4 anos",
            "percentage": 100.0,
            "classification": "Adequado",
        },
    },
    "chronological_age_months": 48,
}


def test_cabecalho_da_tabela_e_o_de_idade_de_desenvolvimento():
    cabecalho = _cabecalho_tabela_pontuacao(COMPUTED)

    assert "Idade De Desenvolvimento" in cabecalho
    assert "Pontuação</th>" not in cabecalho


def test_linhas_da_tabela_mostram_idade_e_percentual_por_area():
    linhas = _linhas_pontuacao(SCHEMA, COMPUTED)

    assert "3 anos e 2 meses (80.0%)" in linhas
    assert "Atraso leve" in linhas
    assert "4 anos (100.0%)" in linhas
    assert "Adequado" in linhas


def test_grafico_e_gerado_a_partir_do_percentual_por_area():
    grafico = _gerar_grafico(SCHEMA, COMPUTED)

    assert grafico is not None
    assert grafico.startswith("data:image/png;base64,")


def test_computed_sem_areas_nem_scores_nao_gera_grafico_nem_linhas():
    assert _gerar_grafico(SCHEMA, {}) is None
    assert _linhas_pontuacao(SCHEMA, {}) == ""
