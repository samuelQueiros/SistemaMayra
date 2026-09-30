def _registrar(client, email="mayra@example.com", password="senhaSegura123"):
    return client.post(
        "/api/auth/register",
        json={"name": "Mayra Vanessa", "email": email, "password": password},
    )


def test_registrar_novo_psicologo(client):
    response = _registrar(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "mayra@example.com"
    assert "password" not in body
    assert "password_hash" not in body


def test_nao_permite_email_duplicado(client):
    _registrar(client)
    response = _registrar(client)

    assert response.status_code == 400


def test_login_com_senha_errada_falha(client):
    _registrar(client)

    response = client.post(
        "/api/auth/login",
        json={"email": "mayra@example.com", "password": "senha-errada"},
    )

    assert response.status_code == 401


def test_login_com_credenciais_corretas_retorna_token(client):
    _registrar(client)

    response = client.post(
        "/api/auth/login",
        json={"email": "mayra@example.com", "password": "senhaSegura123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


def test_me_sem_token_retorna_401(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_me_com_token_valido_retorna_o_proprio_psicologo(client):
    _registrar(client)
    login = client.post(
        "/api/auth/login",
        json={"email": "mayra@example.com", "password": "senhaSegura123"},
    )
    token = login.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "mayra@example.com"


def test_me_com_token_invalido_retorna_401(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer token-invalido"})

    assert response.status_code == 401


def test_atualizar_perfil_grava_bio_e_credenciais_da_assinatura(client):
    _registrar(client)
    login = client.post(
        "/api/auth/login",
        json={"email": "mayra@example.com", "password": "senhaSegura123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put(
        "/api/auth/me",
        headers=headers,
        json={
            "professional_registration": "CRP 00/00000",
            "bio_profissional": "Texto de teste do bloco sobre a profissional.",
            "credenciais_assinatura": "Título De Teste\nSegunda Linha De Teste",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["professional_registration"] == "CRP 00/00000"
    assert body["bio_profissional"] == "Texto de teste do bloco sobre a profissional."
    assert body["credenciais_assinatura"] == "Título De Teste\nSegunda Linha De Teste"

    resposta_me = client.get("/api/auth/me", headers=headers)
    assert resposta_me.json()["bio_profissional"] == "Texto de teste do bloco sobre a profissional."


def test_atualizar_perfil_sem_bio_limpa_o_campo(client):
    _registrar(client)
    login = client.post(
        "/api/auth/login",
        json={"email": "mayra@example.com", "password": "senhaSegura123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.put("/api/auth/me", headers=headers, json={"bio_profissional": "Algo"})

    response = client.put("/api/auth/me", headers=headers, json={})

    assert response.status_code == 200
    assert response.json()["bio_profissional"] is None


def test_apos_5_tentativas_erradas_a_6a_e_bloqueada_mesmo_com_senha_certa(client):
    _registrar(client, email="forca-bruta@example.com", password="senhaSegura123")

    for _ in range(5):
        resposta_errada = client.post(
            "/api/auth/login",
            json={"email": "forca-bruta@example.com", "password": "senha-errada"},
        )
        assert resposta_errada.status_code == 401

    bloqueado = client.post(
        "/api/auth/login",
        json={"email": "forca-bruta@example.com", "password": "senhaSegura123"},
    )

    assert bloqueado.status_code == 429


def test_login_correto_limpa_o_contador_de_tentativas_falhas(client):
    _registrar(client, email="login-normal@example.com", password="senhaSegura123")

    client.post(
        "/api/auth/login",
        json={"email": "login-normal@example.com", "password": "senha-errada"},
    )
    ok = client.post(
        "/api/auth/login",
        json={"email": "login-normal@example.com", "password": "senhaSegura123"},
    )
    assert ok.status_code == 200

    # depois de um login certo, o contador zera — outra tentativa errada
    # sozinha não deveria bloquear nada.
    outra_tentativa_errada = client.post(
        "/api/auth/login",
        json={"email": "login-normal@example.com", "password": "senha-errada"},
    )
    assert outra_tentativa_errada.status_code == 401
