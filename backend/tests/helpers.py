def registrar_e_logar(client, email="mayra@example.com", password="senhaSegura123", name="Mayra"):
    client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    login = client.post("/api/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
