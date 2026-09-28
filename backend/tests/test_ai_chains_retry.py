import pytest

from app.services.ai.chains import _invocar_com_retentativas, _truncar


class _ChatModelFalsoQueFalhaNVezes:
    def __init__(self, falhas_antes_de_funcionar: int, resultado="ok"):
        self.chamadas = 0
        self._falhas_antes_de_funcionar = falhas_antes_de_funcionar
        self._resultado = resultado

    def invoke(self, messages):
        self.chamadas += 1
        if self.chamadas <= self._falhas_antes_de_funcionar:
            raise RuntimeError("Error code: 429 - rate limited")
        return self._resultado


def test_retentativa_recupera_apos_falha_transitoria(monkeypatch):
    monkeypatch.setattr("app.services.ai.chains.time.sleep", lambda *_: None)
    chat_model = _ChatModelFalsoQueFalhaNVezes(falhas_antes_de_funcionar=2)

    resultado = _invocar_com_retentativas(chat_model, [], tentativas=3)

    assert resultado == "ok"
    assert chat_model.chamadas == 3


def test_retentativa_repassa_o_erro_apos_esgotar_tentativas(monkeypatch):
    monkeypatch.setattr("app.services.ai.chains.time.sleep", lambda *_: None)
    chat_model = _ChatModelFalsoQueFalhaNVezes(falhas_antes_de_funcionar=99)

    with pytest.raises(RuntimeError):
        _invocar_com_retentativas(chat_model, [], tentativas=3)

    assert chat_model.chamadas == 3


def test_truncar_nao_altera_texto_curto():
    assert _truncar("texto curto", limite=100) == "texto curto"


def test_truncar_corta_texto_longo_e_adiciona_reticencias():
    texto = "a" * 50
    resultado = _truncar(texto, limite=10)

    assert resultado == "a" * 10 + "…"
    assert len(resultado) == 11


def test_truncar_remove_html_antes_de_cortar():
    # Ponto 10 da revisão: laudos criados pelo formulário standalone salvam
    # o HTML inteiro do relatório em `generated_text` — truncar sem tirar
    # as tags arrisca mandar markup quebrado pra IA como se fosse texto
    # clínico. `_truncar` precisa extrair só o texto visível primeiro.
    html = "<h2>Conclusão</h2><p>O paciente <strong>apresenta</strong> boa evolução.</p>"

    resultado = _truncar(html, limite=1000)

    assert "<" not in resultado and ">" not in resultado
    assert "O paciente apresenta boa evolução." in resultado


def test_truncar_corta_no_limite_mesmo_apos_remover_html():
    html = "<p>" + "a" * 50 + "</p>"

    resultado = _truncar(html, limite=10)

    assert resultado == "a" * 10 + "…"
