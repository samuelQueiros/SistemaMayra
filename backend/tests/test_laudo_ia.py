import json

import pytest
from weasyprint import HTML

import app.api.laudo_ia as modulo
import app.services.storage as storage_module
from app.services.ai.schemas import ProtocoloPorIA
from app.services.ai.agentes import DocumentoExtraido
from app.services.laudo_ia import CatalogoDoProtocolo, ResultadoDaIA, formatar_catalogo, respostas_para_answers
from tests.helpers import registrar_e_logar


@pytest.fixture(autouse=True)
def usar_storage_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_module, "_LOCAL_STORAGE_ROOT", tmp_path / "storage_teste")


CATALOGO = {
    "campos": [
        {"id": "parto", "secao": "2. Anamnese Inicial", "rotulo": "Parto", "tipo": "opcao",
         "opcoes": [{"valor": "Normal", "rotulo": "Normal"}, {"valor": "Cesáreo", "rotulo": "Cesáreo"}]},
        {"id": "complicacaoParto", "secao": "2. Anamnese Inicial", "rotulo": "Houve Complicação No Parto?", "tipo": "opcao",
         "opcoes": [{"valor": "Sim", "rotulo": "Sim"}, {"valor": "Não", "rotulo": "Não"}]},
        {"id": "cars_0", "secao": "11. Pontuações ATA E CARS", "grupo": "CARS", "rotulo": "Relacionamento", "tipo": "opcao",
         "opcoes": [{"valor": "1", "rotulo": "Normal"}, {"valor": "2", "rotulo": "Leve"}]},
        {"id": "dom_atencao", "secao": "17. Domínios", "rotulo": "Atenção (%)", "tipo": "numero", "min": 0, "max": 100},
        {"id": "hip_tdah", "secao": "9. Hipóteses", "rotulo": "TDAH", "tipo": "marcar"},
        {"id": "queixaFamiliar", "secao": "4. Queixas", "rotulo": "Queixas Familiares", "tipo": "texto"},
    ],
    "contexto": "Habilidades por ano: 2º Ano: Leitura, Escrita",
}

PROTOCOLO = ProtocoloPorIA(
    estudo_de_caso="Criança de 7 anos encaminhada pela escola por desatenção.",
    campos=[
        {"id": "parto", "valor": "Cesáreo"},
        {"id": "complicacaoParto", "valor": "Talvez"},  # fora das opções -> descartado
        {"id": "cars_0", "valor": "Leve"},  # rótulo -> vira o valor "2"
        {"id": "dom_atencao", "valor": "35%"},
        {"id": "hip_tdah", "valor": "sim"},
        {"id": "queixaFamiliar", "valor": "Esquece tarefas."},
        {"id": "campo_inventado", "valor": "x"},  # fora do catálogo -> descartado
    ],
    lacunas=["Sem dados do Portage."],
)


def test_respostas_validadas_contra_o_catalogo():
    answers, descartados = respostas_para_answers(PROTOCOLO, CatalogoDoProtocolo.model_validate(CATALOGO))
    assert answers == {
        "parto": "Cesáreo",
        "cars_0": "2",
        "dom_atencao": "35",
        "hip_tdah": True,
        "queixaFamiliar": "Esquece tarefas.",
        "estudoCaso": "Criança de 7 anos encaminhada pela escola por desatenção.",
    }
    assert set(descartados) == {"complicacaoParto", "campo_inventado"}


def test_catalogo_formatado_para_o_prompt():
    texto = formatar_catalogo(CatalogoDoProtocolo.model_validate(CATALOGO))
    assert "## 2. Anamnese Inicial" in texto
    assert "- [cars_0] Relacionamento · opções: 1=Normal | 2=Leve" in texto
    assert "- [dom_atencao] Atenção (%) · número (0 a 100)" in texto
    assert "Habilidades por ano" in texto


@pytest.fixture
def ia_falsa(monkeypatch):
    chamadas = []

    def fake(**kwargs):
        chamadas.append(kwargs)
        documento = DocumentoExtraido(tipo="formulario", titulo="Anamnese", arquivo="anamnese.pdf", respostas=[])
        return ResultadoDaIA(protocolo=PROTOCOLO, documentos=[documento], tempos={"extracao_s": 1.0, "especialistas_s": 2.0})

    monkeypatch.setattr(modulo, "preencher_protocolo", fake)
    return chamadas


def _pdf(titulo: str) -> bytes:
    return HTML(string=f"<h1>{titulo}</h1><p>Parto: (x) Cesáreo ( ) Normal</p>").write_pdf()


def _preparar(client):
    headers = registrar_e_logar(client)
    client.put(
        "/api/settings/ai",
        json={"provider": "anthropic", "model": "claude-sonnet-5", "api_key": "chave-de-teste-1234"},
        headers=headers,
    )
    pid = client.post("/api/patients", json={"name": "Criança Teste", "birth_date": "2019-02-10", "sex": "Masculino"}, headers=headers).json()["id"]
    return headers, pid


def _enviar(client, headers, pid, catalogo=None, arquivos=None):
    return client.post(
        f"/api/patients/{pid}/laudo-ia",
        headers=headers,
        files=[("arquivos", (n, c, "application/pdf")) for n, c in (arquivos or [("anamnese.pdf", _pdf("Anamnese")), ("cars.pdf", _pdf("CARS"))])],
        data={"data_relatorio": "2026-10-15", "cidade": "Gama – DF", "catalogo": catalogo if catalogo is not None else json.dumps(CATALOGO), "observacoes": "Foco em atenção"},
    )


def _concluir(client, headers, resposta) -> dict:
    """A geração roda em segundo plano: acompanha o andamento até o fim."""
    import time

    assert resposta.status_code == 202, resposta.text
    job_id = resposta.json()["job_id"]
    for _ in range(500):
        andamento = client.get(f"/api/laudo-ia/jobs/{job_id}", headers=headers).json()
        if andamento["status"] in ("concluido", "erro"):
            return andamento
        time.sleep(0.01)
    raise AssertionError("a geração não terminou")


def test_cota_diaria_retorna_orientacao_e_nao_cria_laudo(client, monkeypatch):
    headers, pid = _preparar(client)

    def falhar(**kwargs):
        raise RuntimeError(
            "429 RESOURCE_EXHAUSTED GenerateRequestsPerDayPerProjectPerModel-FreeTier "
            "quotaValue: 20 retryDelay: 77036s"
        )

    monkeypatch.setattr(modulo, "preencher_protocolo", falhar)
    andamento = _concluir(client, headers, _enviar(client, headers, pid))

    assert andamento["status"] == "erro"
    mensagem = andamento["erro"]
    assert "cota diária" in mensagem
    assert "Verifique a chave" not in mensagem
    assert "RESOURCE_EXHAUSTED" not in mensagem
    assert client.get(f"/api/patients/{pid}/reports", headers=headers).json() == []


def test_cria_laudo_do_protocolo_padrao(client, ia_falsa):
    headers, pid = _preparar(client)
    andamento = _concluir(client, headers, _enviar(client, headers, pid))
    assert andamento["status"] == "concluido", andamento
    laudo = client.get(f"/api/reports/{andamento['report_id']}", headers=headers).json()
    assert laudo["answers_json"]["dataRelatorio"] == "2026-10-15"
    assert laudo["answers_json"]["cidade"] == "Gama – DF"
    assert laudo["answers_json"]["parto"] == "Cesáreo"
    assert laudo["answers_json"]["estudoCaso"].startswith("Criança de 7 anos")
    assert laudo["computed_json"]["origem"] == "ia_pdf"
    assert laudo["computed_json"]["lacunas"] == ["Sem dados do Portage."]
    assert [a["nome"] for a in laudo["computed_json"]["arquivos"]] == ["anamnese.pdf", "cars.pdf"]

    # Mesmo template do protocolo padrão (fluxo manual).
    template = client.post("/api/templates/custom-form-avaliacao", headers=headers).json()
    assert laudo["template_id"] == template["id"]

    assert laudo["computed_json"]["documentos"][0]["titulo"] == "Anamnese"
    assert laudo["computed_json"]["tempos"] == {"extracao_s": 1.0, "especialistas_s": 2.0}
    # Guardados para as pendências e para saber se o estudo foi editado.
    assert {c["id"] for c in laudo["computed_json"]["catalogo"]["campos"]} >= {"parto", "cars_0"}
    assert laudo["computed_json"]["estudo_de_caso_ia"].startswith("Criança de 7 anos")

    chamada = ia_falsa[0]
    assert chamada["paciente"].startswith("Criança Teste (") and chamada["paciente"].endswith("sexo Masculino")
    assert {c.id for c in chamada["catalogo"].campos} >= {"parto", "cars_0"}
    assert len(chamada["pdfs"]) == 2 and chamada["com_estudo_de_caso"] is True


def test_catalogo_invalido(client, ia_falsa):
    headers, pid = _preparar(client)
    resposta = _enviar(client, headers, pid, catalogo="{nao e json")
    assert resposta.status_code == 400
    assert not ia_falsa


def test_rejeita_arquivo_que_nao_e_pdf(client, ia_falsa):
    headers, pid = _preparar(client)
    resposta = _enviar(client, headers, pid, arquivos=[("foto.png", b"\x89PNG")])
    assert resposta.status_code == 400
    assert not ia_falsa


def test_paciente_de_outra_psicologa(client, ia_falsa):
    _, pid = _preparar(client)
    outra = registrar_e_logar(client, email="outra@exemplo.com")
    resposta = _enviar(client, outra, pid)
    assert resposta.status_code == 404


# A leitura dos PDFs e os especialistas têm testes próprios: tests/test_ai_agentes.py.


def test_catalogo_real_do_formulario_e_aceito():
    """Catálogo gerado por catalogoParaIA() no formulário (paciente de 7 anos):
    as opções da CARS trazem a descrição clínica longa de cada grau."""
    from pathlib import Path

    dados = json.loads((Path(__file__).parent / "fixtures_catalogo_protocolo.json").read_text(encoding="utf-8"))
    catalogo = CatalogoDoProtocolo.model_validate(dados)
    ids = {c.id for c in catalogo.campos}
    assert {"parto", "complicacaoParto", "cars_0", "ata_item_0", "snap_0", "hip_tdah", "anoEscolar", "hab_status_0"} <= ids
    assert any(i.startswith("portage_") for i in ids)
    assert "estudoCaso" not in ids and "nomePaciente" not in ids
    texto = formatar_catalogo(catalogo)
    assert "Grau leve de anormalidade" in texto


def test_escalas_de_pdf_devolve_so_as_respostas(client, ia_falsa):
    headers, pid = _preparar(client)
    resposta = client.post(
        f"/api/patients/{pid}/escalas-de-pdf",
        headers=headers,
        files=[("arquivos", ("cars.pdf", _pdf("CARS"), "application/pdf"))],
        data={"catalogo": json.dumps(CATALOGO)},
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["respostas"]["cars_0"] == "2"
    assert "estudoCaso" not in corpo["respostas"]
    assert corpo["lacunas"] == ["Sem dados do Portage."]
    assert ia_falsa[0]["com_estudo_de_caso"] is False
    # Nenhum laudo é criado.
    assert client.get(f"/api/patients/{pid}/reports", headers=headers).json() == []


def test_dados_confirmados_antes_preenchem_o_que_a_ia_deixou_vazio(client, ia_falsa):
    headers, pid = _preparar(client)
    client.patch(
        f"/api/patients/{pid}/dados-complementares",
        json={"campos": {
            "complicacaoParto": {"valor": "Não", "situacao": "preenchido"},  # a IA não preencheu (valor inválido)
            "parto": {"valor": "Normal", "situacao": "preenchido"},  # a IA leu "Cesáreo" no PDF: vale o PDF
            "queixaFamiliar": {"situacao": "nao_informado"},
        }},
        headers=headers,
    )
    andamento = _concluir(client, headers, _enviar(client, headers, pid))
    answers = client.get(f"/api/reports/{andamento['report_id']}", headers=headers).json()["answers_json"]
    assert answers["complicacaoParto"] == "Não"
    assert answers["parto"] == "Cesáreo"
    assert answers["queixaFamiliar"] == "Esquece tarefas."  # dispensado nunca apaga o que a IA leu


@pytest.mark.parametrize('metadados', [{}, {'data_relatorio': 'inválida'}, {'data_relatorio': '2026-02-30'}, {'data_relatorio': '2026-10-15', 'cidade': 'Cidade inválida'}])
def test_exige_data_valida_e_cidade_do_sistema(client, metadados):
    headers, pid = _preparar(client)
    resposta = client.post(f'/api/patients/{pid}/laudo-ia', headers=headers,
        files=[('arquivos', ('teste.pdf', b'%PDF-1.4', 'application/pdf'))],
        data={'catalogo': json.dumps(CATALOGO), **metadados})
    assert resposta.status_code == 422


def test_escolhas_da_profissional_ata_calculada_e_metodos(client, monkeypatch):
    """Hipóteses e encaminhamentos vêm da tela (a IA nem recebe esses campos),
    a ATA é pontuada pelo sistema e os métodos seguem os PDFs enviados."""
    from tests.test_ata import _documento

    chamadas = []

    def fake(**kwargs):
        chamadas.append(kwargs)
        return ResultadoDaIA(protocolo=PROTOCOLO, documentos=[_documento()], tempos={})

    monkeypatch.setattr(modulo, "preencher_protocolo", fake)
    catalogo = json.loads(json.dumps(CATALOGO))
    catalogo["campos"] += [
        {"id": "hip_tea", "secao": "9. Hipóteses", "rotulo": "TEA", "tipo": "marcar"},
        {"id": "hip_tea_6a02_0", "secao": "9. Hipóteses", "rotulo": "TEA 6A02.0", "tipo": "marcar"},
        {"id": "enc_fonoaudiologia", "secao": "19. Encaminhamentos", "rotulo": "Fonoaudiologia", "tipo": "marcar"},
        *({"id": f"ata_item_{i}", "secao": "11. Pontuações ATA E CARS", "rotulo": f"Item {i}", "tipo": "opcao",
           "opcoes": [{"valor": v, "rotulo": v} for v in "012"]} for i in range(22)),
        *({"id": f"ata_perc_{i}", "secao": "11. Pontuações ATA E CARS", "rotulo": f"% {i}", "tipo": "numero"} for i in range(22)),
        {"id": "snap_0", "secao": "14. SNAP-IV", "rotulo": "Item 1", "tipo": "opcao", "opcoes": [{"valor": "0", "rotulo": "0"}]},
    ]
    headers, pid = _preparar(client)
    resposta = client.post(
        f"/api/patients/{pid}/laudo-ia",
        headers=headers,
        files=[("arquivos", ("ata.pdf", _pdf("ATA"), "application/pdf"))],
        data={
            "data_relatorio": "2026-10-15",
            "catalogo": json.dumps(catalogo),
            "hipoteses": json.dumps(["hip_tea", "hip_tea_6a02_0", "hip_inexistente"]),
            "encaminhamentos": json.dumps(["enc_fonoaudiologia", "parto"]),
        },
    )
    andamento = _concluir(client, headers, resposta)
    assert andamento["status"] == "concluido", andamento
    answers = client.get(f"/api/reports/{andamento['report_id']}", headers=headers).json()["answers_json"]

    assert answers["hip_tea"] is True and answers["hip_tea_6a02_0"] is True
    assert answers["enc_fonoaudiologia"] is True
    assert "hip_inexistente" not in answers and answers.get("parto") == "Cesáreo"  # "parto" não vira caixa marcada
    assert answers["ata_item_17"] == "2" and answers["ata_perc_0"] == "14"
    assert "ata" not in answers  # o total fica com o formulário (campo fora do catálogo)
    assert set(answers["__metodosExcluidos"]) == {"snap", "tod", "portage", "mchat"}  # ATA (PDF) e CARS (respondida) ficam


def test_ia_nao_recebe_o_que_a_profissional_escolhe():
    from app.services.laudo_ia import dividir_catalogo

    catalogo = CatalogoDoProtocolo.model_validate(
        {"campos": CATALOGO["campos"] + [
            {"id": "enc_neuropediatra", "secao": "19. Encaminhamentos", "rotulo": "Neuropediatra", "tipo": "marcar"},
            {"id": "hab_status_0", "secao": "8. Habilidades Acadêmicas", "rotulo": "Hab 0", "tipo": "texto"},
            {"id": "hab_obs_0", "secao": "8. Habilidades Acadêmicas", "rotulo": "Obs 0", "tipo": "texto"},
            {"id": "anoEscolar", "secao": "1. Identificação", "rotulo": "Ano Escolar", "tipo": "texto"},
            {"id": "desfralde", "secao": "3. Histórico", "rotulo": "Desfralde", "tipo": "texto"},
            {"id": "desfraldeAno", "secao": "3. Histórico", "rotulo": "Idade", "tipo": "texto"},
            {"id": "desfraldeMes", "secao": "3. Histórico", "rotulo": "Idade", "tipo": "texto"},
            {"id": "andouAno", "secao": "3. Histórico", "rotulo": "Andou", "tipo": "texto"},
        ]}
    )
    ids = {c.id for parte in dividir_catalogo(catalogo).values() for c in parte.campos}
    # A IA escreve a observação de cada habilidade e os demais marcos.
    assert {"parto", "cars_0", "hab_obs_0", "andouAno"} <= ids
    assert not {"hip_tdah", "enc_neuropediatra", "hab_status_0", "anoEscolar", "desfralde", "desfraldeAno", "desfraldeMes"} & ids


def test_desfralde_ano_escolar_e_habilidades_escolhidos_pela_profissional(client, monkeypatch):
    chamadas = []

    def fake(**kwargs):
        chamadas.append(kwargs)
        protocolo = ProtocoloPorIA(estudo_de_caso="Estudo.", lacunas=[], campos=[
            {"id": "parto", "valor": "Cesáreo"},
            {"id": "desfralde", "valor": "Em Processo"},  # a IA não decide: prevalece a escolha
        ])
        return ResultadoDaIA(protocolo=protocolo, documentos=[], tempos={})

    monkeypatch.setattr(modulo, "preencher_protocolo", fake)
    opcoes = lambda lista: [{"valor": v, "rotulo": v} for v in lista]  # noqa: E731
    catalogo = json.loads(json.dumps(CATALOGO))
    catalogo["campos"] += [
        {"id": "desfralde", "secao": "3. Histórico", "rotulo": "Desfralde", "tipo": "opcao", "opcoes": opcoes(["Controle Total", "Em Processo"])},
        {"id": "desfraldeAno", "secao": "3. Histórico", "rotulo": "Idade", "tipo": "opcao", "opcoes": opcoes(["2 anos", "3 anos"])},
        {"id": "desfraldeMes", "secao": "3. Histórico", "rotulo": "Idade", "tipo": "opcao", "opcoes": opcoes(["0 meses", "6 meses"])},
        {"id": "anoEscolar", "secao": "1. Identificação", "rotulo": "Ano Escolar", "tipo": "opcao", "opcoes": opcoes(["1º Ano", "2º Ano"])},
        {"id": "hab_status_0", "secao": "8. Habilidades Acadêmicas", "rotulo": "Hab 0", "tipo": "opcao", "opcoes": opcoes(["Satisfatório", "Em Desenvolvimento"])},
        {"id": "hab_status_1", "secao": "8. Habilidades Acadêmicas", "rotulo": "Hab 1", "tipo": "opcao", "opcoes": opcoes(["Satisfatório", "Em Desenvolvimento"])},
    ]
    catalogo["contexto"] = "Habilidades acadêmicas:\n- 2º Ano: 0=Leitura De Textos Curtos; 1=Escrita De Frases"
    headers, pid = _preparar(client)
    resposta = client.post(
        f"/api/patients/{pid}/laudo-ia",
        headers=headers,
        files=[("arquivos", ("anamnese.pdf", _pdf("Anamnese"), "application/pdf"))],
        data={
            "data_relatorio": "2026-10-15",
            "catalogo": json.dumps(catalogo),
            "observacoes": "Foco em atenção",
            "dados_profissional": json.dumps({
                "desfralde": "Controle Total", "desfraldeAno": "3 anos", "desfraldeMes": "6 meses",
                "anoEscolar": "2º Ano", "hab_status_0": "Em Desenvolvimento", "hab_status_1": "Satisfatório",
                "hab_status_9": "Satisfatório",  # fora do catálogo
                "desfraldeMes_x": "6 meses", "parto": "Normal",  # não é escolha da profissional
                "anoEscolar_invalido": 3,
            }),
        },
    )
    andamento = _concluir(client, headers, resposta)
    assert andamento["status"] == "concluido", andamento
    answers = client.get(f"/api/reports/{andamento['report_id']}", headers=headers).json()["answers_json"]
    assert (answers["desfralde"], answers["desfraldeAno"], answers["desfraldeMes"]) == ("Controle Total", "3 anos", "6 meses")
    assert (answers["anoEscolar"], answers["hab_status_0"], answers["hab_status_1"]) == ("2º Ano", "Em Desenvolvimento", "Satisfatório")
    assert answers["parto"] == "Cesáreo" and "hab_status_9" not in answers
    # A IA recebe as escolhas como dados confirmados, junto das observações.
    observacoes = chamadas[0]["observacoes"]
    assert observacoes.startswith("Foco em atenção")
    assert "Desfralde: Controle Total, com 3 anos e 6 meses" in observacoes
    assert "Habilidade nº 0 (Leitura De Textos Curtos): Em Desenvolvimento" in observacoes
    assert "Habilidade nº 1 (Escrita De Frases): Satisfatório" in observacoes
    # As observações guardadas no laudo continuam só as da psicóloga.
    laudo = client.get(f"/api/reports/{andamento['report_id']}", headers=headers).json()
    assert laudo["computed_json"]["observacoes"] == "Foco em atenção"


def test_dados_da_profissional_invalidos_dao_400(client):
    headers, pid = _preparar(client)
    resposta = client.post(
        f"/api/patients/{pid}/laudo-ia",
        headers=headers,
        files=[("arquivos", ("anamnese.pdf", _pdf("Anamnese"), "application/pdf"))],
        data={"data_relatorio": "2026-10-15", "catalogo": json.dumps(CATALOGO), "dados_profissional": "[1, 2]"},
    )
    assert resposta.status_code == 400


def _catalogo_de_idades() -> CatalogoDoProtocolo:
    anos = ["Antes de 1 ano", "1 ano", "2 anos", "3 anos", "4 anos", "5 anos", "6 anos ou mais", "Não informado"]
    meses = ["0 meses", "1 mês"] + [f"{n} meses" for n in range(2, 12)] + ["Não informado"]
    opcoes = lambda lista: [{"valor": v, "rotulo": v} for v in lista]  # noqa: E731
    return CatalogoDoProtocolo.model_validate({"campos": [
        {"id": "desfralde", "secao": "3. Histórico", "tipo": "opcao", "opcoes": opcoes(["Controle Total", "Em Processo"])},
        {"id": "desfraldeAno", "secao": "3. Histórico", "tipo": "opcao", "opcoes": opcoes(anos)},
        {"id": "desfraldeMes", "secao": "3. Histórico", "tipo": "opcao", "opcoes": opcoes(meses)},
        {"id": "andouAno", "secao": "3. Histórico", "tipo": "opcao", "opcoes": opcoes(anos)},
        {"id": "andouMes", "secao": "3. Histórico", "tipo": "opcao", "opcoes": opcoes(meses)},
        {"id": "falouAno", "secao": "3. Histórico", "tipo": "opcao", "opcoes": opcoes(anos)},
        {"id": "falouMes", "secao": "3. Histórico", "tipo": "opcao", "opcoes": opcoes(meses)},
    ]})


def test_idade_inteira_no_campo_de_anos_e_dividida_em_ano_e_mes():
    from app.services.ai.schemas import ProtocoloPorIA

    protocolo = ProtocoloPorIA(estudo_de_caso="", lacunas=[], campos=[
        {"id": "desfralde", "valor": "Controle Total"},
        {"id": "desfraldeAno", "valor": "2 anos e 6 meses"},
        {"id": "andouAno", "valor": "18 meses"},
        {"id": "falouAno", "valor": "com 3 anos e meio"},
        {"id": "falouMes", "valor": "4 meses"},  # o mês preenchido pela IA prevalece
    ])
    answers, descartados = respostas_para_answers(protocolo, _catalogo_de_idades())
    assert answers["desfralde"] == "Controle Total"
    assert (answers["desfraldeAno"], answers["desfraldeMes"]) == ("2 anos", "6 meses")
    assert (answers["andouAno"], answers["andouMes"]) == ("1 ano", "6 meses")
    assert (answers["falouAno"], answers["falouMes"]) == ("3 anos", "4 meses")
    assert descartados == []


def test_idade_acima_da_ultima_opcao_vai_para_ou_mais():
    from app.services.ai.schemas import ProtocoloPorIA

    protocolo = ProtocoloPorIA(estudo_de_caso="", lacunas=[], campos=[{"id": "desfraldeAno", "valor": "7 anos"}])
    answers, _ = respostas_para_answers(protocolo, _catalogo_de_idades())
    assert answers["desfraldeAno"] == "6 anos ou mais" and answers["desfraldeMes"] == "0 meses"
