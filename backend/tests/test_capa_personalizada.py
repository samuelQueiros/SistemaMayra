import pytest

import app.services.storage as storage_module
from tests.helpers import registrar_e_logar


@pytest.fixture(autouse=True)
def usar_storage_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_module, "_LOCAL_STORAGE_ROOT", tmp_path / "storage_teste")


def _png(conteudo: bytes = b"capa-1") -> bytes:
    # O serviço só guarda os bytes; a validação é pela extensão.
    return b"\x89PNG\r\n\x1a\n" + conteudo


def _enviar(client, headers, nome="capa.png", conteudo=None):
    return client.put(
        "/api/auth/me/capa",
        headers=headers,
        files={"file": (nome, conteudo if conteudo is not None else _png(), "image/png")},
    )


CONFIG_VALIDA = {
    "escreverNome": True,
    "faixa": {"x": 0.2, "y": 0.4, "largura": 0.6, "altura": 0.05},
    "corNome": "#5b2a86",
}


def test_sem_capa_personalizada_por_padrao(client):
    headers = registrar_e_logar(client)
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["tem_capa_personalizada"] is False
    assert me["capa_config"] is None
    assert client.get("/api/auth/me/capa/arquivo", headers=headers).status_code == 404


def test_envia_baixa_e_troca_a_capa(client, tmp_path):
    headers = registrar_e_logar(client)

    resposta = _enviar(client, headers)
    assert resposta.status_code == 200
    assert resposta.json()["tem_capa_personalizada"] is True
    baixada = client.get("/api/auth/me/capa/arquivo", headers=headers)
    assert baixada.status_code == 200
    assert baixada.content == _png()
    assert baixada.headers["content-type"] == "image/png"

    _enviar(client, headers, nome="nova.jpg", conteudo=b"\xff\xd8capa-2")
    assert client.get("/api/auth/me/capa/arquivo", headers=headers).content == b"\xff\xd8capa-2"
    # A capa anterior é apagada do storage ao ser substituída.
    arquivos = [p for p in (tmp_path / "storage_teste" / "covers").rglob("*") if p.is_file()]
    assert len(arquivos) == 1


def test_remove_a_capa_e_a_configuracao(client):
    headers = registrar_e_logar(client)
    _enviar(client, headers)
    client.put("/api/auth/me/capa/config", headers=headers, json=CONFIG_VALIDA)

    resposta = client.delete("/api/auth/me/capa", headers=headers)

    assert resposta.status_code == 200
    assert resposta.json()["tem_capa_personalizada"] is False
    assert resposta.json()["capa_config"] is None
    assert client.get("/api/auth/me/capa/arquivo", headers=headers).status_code == 404


def test_rejeita_formato_nao_suportado(client):
    headers = registrar_e_logar(client)
    resposta = _enviar(client, headers, nome="capa.pdf", conteudo=b"%PDF-1.4")
    assert resposta.status_code == 400
    assert "JPG, PNG ou WEBP" in resposta.json()["detail"]


def test_rejeita_arquivo_grande_demais(client):
    headers = registrar_e_logar(client)
    resposta = _enviar(client, headers, conteudo=b"0" * (10 * 1024 * 1024 + 1))
    assert resposta.status_code == 413


def test_salva_configuracao_da_capa(client):
    headers = registrar_e_logar(client)
    resposta = client.put("/api/auth/me/capa/config", headers=headers, json=CONFIG_VALIDA)
    assert resposta.status_code == 200
    assert resposta.json()["capa_config"] == CONFIG_VALIDA
    assert client.get("/api/auth/me", headers=headers).json()["capa_config"] == CONFIG_VALIDA


@pytest.mark.parametrize(
    "alteracao",
    [
        {"corNome": "branco"},
        {"faixa": {"x": -0.1, "y": 0.4, "largura": 0.5, "altura": 0.05}},
        {"faixa": {"x": 0.7, "y": 0.4, "largura": 0.5, "altura": 0.05}},
        {"faixa": {"x": 0.2, "y": 0.4, "largura": 0, "altura": 0.05}},
    ],
)
def test_rejeita_configuracao_invalida(client, alteracao):
    headers = registrar_e_logar(client)
    resposta = client.put("/api/auth/me/capa/config", headers=headers, json={**CONFIG_VALIDA, **alteracao})
    assert resposta.status_code == 422


def test_capa_de_uma_psicologa_nao_aparece_para_outra(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    _enviar(client, headers_a)

    assert client.get("/api/auth/me/capa/arquivo", headers=headers_b).status_code == 404
    assert client.get("/api/auth/me", headers=headers_b).json()["tem_capa_personalizada"] is False


def test_rotas_da_capa_exigem_login(client):
    assert client.get("/api/auth/me/capa/arquivo").status_code == 401
    assert client.put("/api/auth/me/capa", files={"file": ("c.png", _png(), "image/png")}).status_code == 401
    assert client.put("/api/auth/me/capa/config", json=CONFIG_VALIDA).status_code == 401
    assert client.delete("/api/auth/me/capa").status_code == 401
