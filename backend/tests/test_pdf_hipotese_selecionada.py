from types import SimpleNamespace

from app.services.pdf_do_laudo import _secoes_clinicas_html


def _relatorio_com_secoes(secoes: dict):
    return SimpleNamespace(clinical_sections_json=secoes)


def test_mostra_apenas_a_hipotese_marcada_como_selecionada():
    report = _relatorio_com_secoes(
        {
            "diagnostic_hypotheses": [
                {"label": "TDAH - Transtorno Fictício De Atenção", "cid": "6A05", "selected": False},
                {"label": "TEA - Transtorno Fictício Do Espectro", "cid": "6A02", "selected": True},
            ]
        }
    )

    html = _secoes_clinicas_html(report)

    assert "TEA - Transtorno Fictício Do Espectro" in html
    assert "TDAH - Transtorno Fictício De Atenção" not in html
    assert html.count("<li>") == 1


def test_sem_hipotese_marcada_usa_a_primeira_sem_listar_as_demais():
    report = _relatorio_com_secoes(
        {
            "diagnostic_hypotheses": [
                {"label": "Hipótese Fictícia A", "cid": None, "selected": False},
                {"label": "Hipótese Fictícia B", "cid": None, "selected": False},
            ]
        }
    )

    html = _secoes_clinicas_html(report)

    assert "Hipótese Fictícia A" in html
    assert "Hipótese Fictícia B" not in html
    assert html.count("<li>") == 1


def test_sem_hipoteses_nao_gera_bloco():
    report = _relatorio_com_secoes({"diagnostic_hypotheses": []})

    html = _secoes_clinicas_html(report)

    assert "Hipótese Diagnóstica" not in html
