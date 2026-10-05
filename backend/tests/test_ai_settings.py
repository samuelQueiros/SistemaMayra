from app.models.ai_settings import AISettings
from tests.helpers import registrar_e_logar


def test_exige_autenticacao(client):
    response = client.get("/api/settings/ai")

    assert response.status_code == 401


def test_sem_configuracao_mostra_nao_configurado(client):
    headers = registrar_e_logar(client)

    response = client.get("/api/settings/ai", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["api_key_configured"] is False


def test_salva_e_le_configuracao_de_ia(client):
    headers = registrar_e_logar(client)

    put_response = client.put(
        "/api/settings/ai",
        json={"provider": "anthropic", "model": "claude-sonnet-5", "api_key": "sk-teste-12345678"},
        headers=headers,
    )
    assert put_response.status_code == 200
    body = put_response.json()
    assert body["provider"] == "anthropic"
    assert body["model"] == "claude-sonnet-5"
    assert body["api_key_configured"] is True
    # a chave nunca volta em texto puro na resposta
    assert "sk-teste-12345678" not in put_response.text
    assert body["api_key_preview"].endswith("5678")

    get_response = client.get("/api/settings/ai", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["api_key_configured"] is True


def test_chave_fica_criptografada_no_banco(client):
    headers = registrar_e_logar(client)
    client.put(
        "/api/settings/ai",
        json={"provider": "anthropic", "model": "claude-sonnet-5", "api_key": "sk-segredo-nao-pode-vazar"},
        headers=headers,
    )

    db = client.db_session_factory()
    try:
        row = db.query(AISettings).first()
        assert row is not None
        assert row.api_key != "sk-segredo-nao-pode-vazar"
        assert "sk-segredo-nao-pode-vazar" not in row.api_key
    finally:
        db.close()


def test_atualizar_configuracao_substitui_a_anterior(client):
    headers = registrar_e_logar(client)
    client.put(
        "/api/settings/ai",
        json={"provider": "anthropic", "model": "claude-sonnet-5", "api_key": "chave-antiga-0000"},
        headers=headers,
    )

    response = client.put(
        "/api/settings/ai",
        json={"provider": "openai", "model": "gpt-5", "api_key": "chave-nova-9999"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "openai"
    assert body["model"] == "gpt-5"
    assert body["api_key_preview"].endswith("9999")


def test_aceita_provedor_google(client):
    headers = registrar_e_logar(client)

    response = client.put(
        "/api/settings/ai",
        json={"provider": "google", "model": "gemini-3.6-flash", "api_key": "chave-gemini-teste"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "google"


def test_configuracao_de_ia_e_isolada_por_psicologa(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    client.put(
        "/api/settings/ai",
        json={"provider": "anthropic", "model": "claude-sonnet-5", "api_key": "chave-da-a"},
        headers=headers_a,
    )

    response = client.get("/api/settings/ai", headers=headers_b)

    assert response.status_code == 200
    assert response.json()["api_key_configured"] is False


def test_aceita_os_novos_provedores_e_recusa_desconhecido(client):
    headers = registrar_e_logar(client)
    for provider, modelo in [("xai", "grok-4"), ("deepseek", "deepseek-chat"), ("openrouter", "openai/gpt-5"), ("mistral", "mistral-large-latest")]:
        resposta = client.put("/api/settings/ai", json={"provider": provider, "model": modelo, "api_key": "chave-1234"}, headers=headers)
        assert resposta.status_code == 200, resposta.text
        assert resposta.json()["provider"] == provider
    resposta = client.put("/api/settings/ai", json={"provider": "inventado", "model": "x", "api_key": "chave-1234"}, headers=headers)
    assert resposta.status_code == 422


def test_lista_os_provedores_para_a_tela(client):
    headers = registrar_e_logar(client)
    provedores = client.get("/api/settings/ai/provedores", headers=headers).json()
    ids = [p["id"] for p in provedores]
    assert {"anthropic", "openai", "google", "openrouter", "xai", "mistral", "groq", "qwen", "deepseek", "cohere"} <= set(ids)
    deepseek = next(p for p in provedores if p["id"] == "deepseek")
    assert deepseek["leitura_pdf"] == "texto"
    assert "não lê imagens" in deepseek["observacao"]
    assert client.get("/api/settings/ai/provedores").status_code == 401
