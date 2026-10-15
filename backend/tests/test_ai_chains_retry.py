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


def test_cota_diaria_nao_repete_chamada_nem_espera(monkeypatch):
    from unittest.mock import Mock

    erro = RuntimeError("429 RESOURCE_EXHAUSTED GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    modelo = Mock()
    modelo.invoke.side_effect = erro
    espera = Mock()
    monkeypatch.setattr("app.services.ai.chains.time.sleep", espera)

    with pytest.raises(RuntimeError) as recebido:
        _invocar_com_retentativas(modelo, [])

    assert recebido.value is erro
    modelo.invoke.assert_called_once()
    espera.assert_not_called()


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


class _ErroDoProvedor(Exception):
    def __init__(self, status_code, mensagem="erro"):
        super().__init__(mensagem)
        self.status_code = status_code


def test_erro_de_configuracao_nao_e_repetido(monkeypatch):
    from unittest.mock import Mock

    espera = Mock()
    monkeypatch.setattr("app.services.ai.chains.time.sleep", espera)
    modelo = Mock()
    modelo.invoke.side_effect = _ErroDoProvedor(401, "invalid api key")

    with pytest.raises(_ErroDoProvedor):
        _invocar_com_retentativas(modelo, [])

    modelo.invoke.assert_called_once()
    espera.assert_not_called()


def test_limite_por_minuto_espera_o_tempo_pedido_pelo_provedor(monkeypatch):
    esperas = []
    monkeypatch.setattr("app.services.ai.chains.time.sleep", esperas.append)

    class Falha429(_ChatModelFalsoQueFalhaNVezes):
        def invoke(self, messages):
            self.chamadas += 1
            if self.chamadas == 1:
                raise _ErroDoProvedor(429, "Rate limit reached for tokens per min. Please try again in 8.5s.")
            return "ok"

    assert _invocar_com_retentativas(Falha429(0), []) == "ok"
    assert esperas == [9.5]  # o pedido + 1 s de folga (antes: 1,5 s fixo)


def test_tempo_esgotado_tenta_so_mais_uma_vez(monkeypatch):
    from unittest.mock import Mock

    monkeypatch.setattr("app.services.ai.chains.time.sleep", lambda *_: None)

    class APITimeoutError(Exception):
        pass

    modelo = Mock()
    modelo.invoke.side_effect = APITimeoutError("Request timed out.")
    with pytest.raises(APITimeoutError):
        _invocar_com_retentativas(modelo, [], tentativas=3)
    assert modelo.invoke.call_count == 2
