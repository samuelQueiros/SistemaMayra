from tests.helpers import registrar_e_logar

TEMPLATE_VALIDO = {
    "name": "Escala CARS (reduzida para teste)",
    "version": 1,
    "schema_json": {
        "name": "Escala CARS",
        "areas": [
            {
                "key": "comunicacao",
                "label": "Comunicação",
                "fields": [
                    {
                        "key": "iniciativa_social",
                        "label": "Iniciativa de interação social",
                        "type": "scale",
                        "min": 1,
                        "max": 4,
                        "weight": 1,
                    }
                ],
            }
        ],
        "classification_ranges": [
            {"label": "Normal", "min": 15, "max": 29.5},
            {"label": "Leve-moderado", "min": 30, "max": 36.5},
            {"label": "Grave", "min": 37, "max": 60},
        ],
        "chart": {"type": "bar", "group_by": "areas"},
    },
}


def test_exige_autenticacao_para_listar_templates(client):
    response = client.get("/api/templates")

    assert response.status_code == 401


def test_cria_template_valido(client):
    headers = registrar_e_logar(client)

    response = client.post("/api/templates", json=TEMPLATE_VALIDO, headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Escala CARS (reduzida para teste)"
    assert body["schema_json"]["rule_type"] == "sum_threshold"


def test_rejeita_campo_scale_sem_min_max(client):
    headers = registrar_e_logar(client)
    template = _template_com_campo({"key": "x", "label": "X", "type": "scale", "weight": 1})

    response = client.post("/api/templates", json=template, headers=headers)

    assert response.status_code == 422


def test_rejeita_campo_select_sem_options(client):
    headers = registrar_e_logar(client)
    template = _template_com_campo({"key": "x", "label": "X", "type": "select", "weight": 1})

    response = client.post("/api/templates", json=template, headers=headers)

    assert response.status_code == 422


def test_rejeita_sum_threshold_sem_min_max_na_faixa(client):
    headers = registrar_e_logar(client)
    template = dict(TEMPLATE_VALIDO)
    template["schema_json"] = dict(TEMPLATE_VALIDO["schema_json"])
    template["schema_json"]["classification_ranges"] = [{"label": "Sem faixa numérica"}]

    response = client.post("/api/templates", json=template, headers=headers)

    assert response.status_code == 422


def test_psicologo_nao_acessa_template_de_outro(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")

    created = client.post("/api/templates", json=TEMPLATE_VALIDO, headers=headers_a)
    template_id = created.json()["id"]

    listed_b = client.get("/api/templates", headers=headers_b)
    assert listed_b.json() == []

    get_b = client.get(f"/api/templates/{template_id}", headers=headers_b)
    assert get_b.status_code == 404


def _template_com_campo(field: dict) -> dict:
    template = {
        "name": "Template De Teste",
        "version": 1,
        "schema_json": {
            "name": "Template De Teste",
            "areas": [{"key": "area_1", "label": "Área 1", "fields": [field]}],
            "classification_ranges": [{"label": "Normal", "min": 0, "max": 10}],
            "chart": {"type": "bar", "group_by": "areas"},
        },
    }
    return template
