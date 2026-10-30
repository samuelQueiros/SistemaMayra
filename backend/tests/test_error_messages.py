from app.core.errors import mensagem_de_validacao
from tests.helpers import registrar_e_logar


def test_validacao_vira_frase_em_portugues(client):
    resposta = client.post(
        "/api/auth/register", json={"name": "Mayra", "email": "nao-e-email", "password": "senhaSegura123"}
    )
    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert isinstance(detalhe, str)
    assert detalhe == "Informe um e-mail válido (ex.: nome@exemplo.com)."


def test_campo_obrigatorio_ausente(client):
    headers = registrar_e_logar(client)
    resposta = client.post("/api/patients", json={"birth_date": "2018-02-10"}, headers=headers)
    assert resposta.status_code == 422
    assert resposta.json()["detail"] == 'Preencha o campo "Nome".'


def test_data_invalida(client):
    headers = registrar_e_logar(client)
    resposta = client.post("/api/patients", json={"name": "Ana", "birth_date": "31/02/2018"}, headers=headers)
    assert resposta.status_code == 422
    assert "Data de nascimento" in resposta.json()["detail"]
    assert "dd/mm/aaaa" in resposta.json()["detail"]


def test_identificador_invalido_na_url(client):
    headers = registrar_e_logar(client)
    resposta = client.get("/api/reports/nao-e-um-id", headers=headers)
    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "O registro solicitado não existe ou o endereço está incorreto."


def test_sessao_expirada_tem_mensagem_clara(client):
    resposta = client.get("/api/patients", headers={"Authorization": "Bearer token-invalido"})
    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "Sua sessão expirou. Entre novamente para continuar."


def test_protocolo_inexistente(client):
    headers = registrar_e_logar(client)
    resposta = client.get("/api/reports/00000000-0000-0000-0000-000000000000", headers=headers)
    assert resposta.status_code == 404
    assert resposta.json()["detail"].startswith("Protocolo não encontrado")


def test_tamanho_minimo_menciona_limite():
    msg = mensagem_de_validacao({"type": "string_too_short", "loc": ("body", "password"), "ctx": {"min_length": 8}})
    assert msg == '"Senha" precisa ter pelo menos 8 caracteres.'
