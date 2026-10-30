import copy

import pytest

import app.services.storage as storage_module
from tests.helpers import registrar_e_logar
from tests.test_documents_export import HTML_LAUDO


@pytest.fixture(autouse=True)
def usar_storage_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_module, "_LOCAL_STORAGE_ROOT", tmp_path / "storage_teste")


MODELO = {
    "name": "Anamnese + SNAP Simplificado",
    "descricao": "Modelo de teste",
    "titulo_relatorio": "PARECER DE TESTE",
    "secoes": [
        {
            "id": "anamnese",
            "titulo": "Anamnese",
            "tipo": "perguntas",
            "perguntas": [
                {"id": "queixa", "rotulo": "Queixa principal", "tipo": "texto_longo"},
                {
                    "id": "parto",
                    "rotulo": "Parto",
                    "tipo": "multipla_escolha",
                    "opcoes": [
                        {"rotulo": "Normal", "texto_relatorio": "Parto normal."},
                        {"rotulo": "Cesárea"},
                    ],
                },
            ],
            "relatorio": {"formato": "lista", "texto_padrao": "Queixa: {q:queixa}. {O} paciente {nome}."},
        },
        {
            "id": "snap",
            "titulo": "SNAP Simplificado",
            "tipo": "escala",
            "escala": {
                "itens": [{"id": "i1", "rotulo": "Item 1"}, {"id": "i2", "rotulo": "Item 2"}],
                "opcoes": [
                    {"rotulo": "Nunca", "valor": 0},
                    {"rotulo": "Às vezes", "valor": 1},
                    {"rotulo": "Sempre", "valor": 2},
                ],
                "faixas": [
                    {"min": 0, "max": 1, "rotulo": "Sem indícios"},
                    {"min": 2, "max": 3, "rotulo": "Leve"},
                    {"min": 4, "max": 4, "rotulo": "Significativo", "texto_relatorio": "Indícios significativos."},
                ],
            },
            "relatorio": {"texto_padrao": "Pontuação {pontuacao}: {classificacao}."},
        },
    ],
}


def _criar(client, headers, modelo=None):
    return client.post("/api/protocolos", json={"schema_json": modelo or MODELO}, headers=headers)


def test_cria_lista_e_le_modelo(client):
    headers = registrar_e_logar(client)
    criado = _criar(client, headers)
    assert criado.status_code == 201
    corpo = criado.json()
    assert corpo["name"] == MODELO["name"]
    assert corpo["schema_json"]["rule_type"] == "protocolo"
    assert corpo["arquivado"] is False

    lista = client.get("/api/protocolos", headers=headers).json()
    assert [m["id"] for m in lista] == [corpo["id"]]
    assert client.get(f"/api/protocolos/{corpo['id']}", headers=headers).status_code == 200


def test_lista_nao_mostra_o_protocolo_fixo_nem_templates_antigos(client):
    headers = registrar_e_logar(client)
    client.post("/api/templates/custom-form-avaliacao", headers=headers)
    assert client.get("/api/protocolos", headers=headers).json() == []


def test_edita_modelo_e_incrementa_versao(client):
    headers = registrar_e_logar(client)
    modelo_id = _criar(client, headers).json()["id"]
    novo = copy.deepcopy(MODELO)
    novo["name"] = "Nome Novo"
    resposta = client.put(f"/api/protocolos/{modelo_id}", json={"schema_json": novo}, headers=headers)
    assert resposta.status_code == 200
    assert resposta.json()["name"] == "Nome Novo"
    assert resposta.json()["version"] == 2


def test_arquivar_esconde_da_lista_e_restaurar_volta(client):
    headers = registrar_e_logar(client)
    modelo_id = _criar(client, headers).json()["id"]

    assert client.delete(f"/api/protocolos/{modelo_id}", headers=headers).json()["arquivado"] is True
    assert client.get("/api/protocolos", headers=headers).json() == []
    assert len(client.get("/api/protocolos?incluir_arquivados=true", headers=headers).json()) == 1

    client.post(f"/api/protocolos/{modelo_id}/restaurar", headers=headers)
    assert len(client.get("/api/protocolos", headers=headers).json()) == 1


def test_duplicar(client):
    headers = registrar_e_logar(client)
    modelo_id = _criar(client, headers).json()["id"]
    copia = client.post(f"/api/protocolos/{modelo_id}/duplicar", headers=headers)
    assert copia.status_code == 201
    assert copia.json()["name"] == MODELO["name"] + " (cópia)"
    assert copia.json()["id"] != modelo_id


@pytest.mark.parametrize(
    "estragar",
    [
        lambda m: m["secoes"][0]["perguntas"][1].update(opcoes=[]),
        lambda m: m["secoes"][0]["perguntas"][1].update(tipo="inexistente"),
        lambda m: m["secoes"][0]["perguntas"].append(dict(m["secoes"][0]["perguntas"][0])),
        lambda m: m["secoes"][0]["relatorio"].update(texto_padrao="{q:nao_existe}"),
        lambda m: m["secoes"][1]["escala"]["faixas"].append({"min": 1, "max": 2, "rotulo": "Sobreposta"}),
        lambda m: m["secoes"][1].update(escala=None),
        lambda m: m.update(secoes=[]),
        lambda m: m["secoes"][0].update(id="Com Espaço"),
    ],
)
def test_rejeita_modelo_invalido(client, estragar):
    headers = registrar_e_logar(client)
    modelo = copy.deepcopy(MODELO)
    estragar(modelo)
    assert _criar(client, headers, modelo).status_code == 422


def test_modelo_de_outra_psicologa_da_404(client):
    headers_a = registrar_e_logar(client, email="a@example.com")
    headers_b = registrar_e_logar(client, email="b@example.com")
    modelo_id = _criar(client, headers_a).json()["id"]

    assert client.get(f"/api/protocolos/{modelo_id}", headers=headers_b).status_code == 404
    assert (
        client.put(f"/api/protocolos/{modelo_id}", json={"schema_json": MODELO}, headers=headers_b).status_code == 404
    )
    assert client.delete(f"/api/protocolos/{modelo_id}", headers=headers_b).status_code == 404
    assert client.get("/api/protocolos", headers=headers_b).json() == []


def test_rotas_exigem_login(client):
    assert client.get("/api/protocolos").status_code == 401
    assert client.post("/api/protocolos", json={"schema_json": MODELO}).status_code == 401


def _criar_laudo(client, headers, modelo_id):
    patient = client.post(
        "/api/patients", json={"name": "Criança Teste", "birth_date": "2018-02-10"}, headers=headers
    ).json()
    return client.post(
        f"/api/patients/{patient['id']}/reports",
        json={"template_id": modelo_id, "answers": {"queixa": "Desatenção"}},
        headers=headers,
    ).json()


def test_laudo_guarda_copia_do_modelo_mesmo_depois_de_editado(client):
    headers = registrar_e_logar(client)
    modelo_id = _criar(client, headers).json()["id"]
    laudo = _criar_laudo(client, headers, modelo_id)
    assert laudo["computed_json"]["modelo"]["name"] == MODELO["name"]

    novo = copy.deepcopy(MODELO)
    novo["name"] = "Editado Depois"
    client.put(f"/api/protocolos/{modelo_id}", json={"schema_json": novo}, headers=headers)

    relido = client.get(f"/api/reports/{laudo['id']}", headers=headers).json()
    assert relido["computed_json"]["modelo"]["name"] == MODELO["name"]


def test_historico_baixa_pdf_e_word_do_laudo_de_modelo(client):
    headers = registrar_e_logar(client)
    modelo_id = _criar(client, headers).json()["id"]
    laudo_id = _criar_laudo(client, headers, modelo_id)["id"]
    client.put(f"/api/reports/{laudo_id}/text", json={"generated_text": HTML_LAUDO}, headers=headers)

    pdf = client.get(f"/api/reports/{laudo_id}/pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    docx = client.get(f"/api/reports/{laudo_id}/docx", headers=headers)
    assert docx.status_code == 200
    assert docx.content.startswith(b"PK")
