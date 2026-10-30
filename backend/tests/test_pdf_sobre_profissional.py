from types import SimpleNamespace

from app.services.pdf_do_laudo import _BIO_PROFISSIONAL_PADRAO, _sobre_a_profissional_html


def _psicologa(bio_profissional=None):
    return SimpleNamespace(bio_profissional=bio_profissional)


def test_usa_bio_configurada_no_perfil_quando_existe():
    psicologa = _psicologa(bio_profissional="Bio fictícia de teste, configurada pela profissional.")

    html = _sobre_a_profissional_html(psicologa)

    assert "Bio fictícia de teste, configurada pela profissional." in html
    assert "Sobre A Profissional Responsável" in html
    assert _BIO_PROFISSIONAL_PADRAO not in html


def test_usa_texto_padrao_quando_perfil_nao_tem_bio_configurada():
    psicologa = _psicologa(bio_profissional=None)

    html = _sobre_a_profissional_html(psicologa)

    assert _BIO_PROFISSIONAL_PADRAO in html


def test_sem_psicologo_nao_gera_bloco():
    assert _sobre_a_profissional_html(None) == ""
