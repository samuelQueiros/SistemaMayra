"""Pendências do laudo (o que faltou depois do Laudo por IA)."""

import json
import re
from pathlib import Path
from uuid import UUID

import pytest

from app.models.report import Report
from app.services.laudo_ia import CatalogoDoProtocolo
from app.services.pendencias import SECOES, Pendencias
from tests.helpers import registrar_e_logar

RAIZ = Path(__file__).resolve().parents[2]
CATALOGO_DADOS = json.loads((Path(__file__).parent / "fixtures_catalogo_protocolo.json").read_text(encoding="utf-8"))
CATALOGO = CatalogoDoProtocolo.model_validate(CATALOGO_DADOS)
IDS = {c.id for c in CATALOGO.campos}


def _montar(answers=None, dados=None, tipos=(), adicionadas=(), sugestoes=()):
    return Pendencias(CATALOGO, answers or {}, dados or {}, list(tipos), list(adicionadas), list(sugestoes)).montar()


def _grupo(resultado, chave):
    return next((g for g in resultado["grupos"] if g["chave"] == chave), None)


def _textos(resultado):
    for g in resultado["grupos"]:
        yield g["titulo"]
        for i in g["itens"]:
            yield i["rotulo"]


# --- cálculo ------------------------------------------------------------------


def test_nenhum_id_tecnico_aparece_como_texto():
    resultado = _montar({"anoEscolar": "2º Ano"}, tipos=["ata", "cars", "snap_iv", "tod", "portage"])
    for texto in _textos(resultado):
        assert texto not in IDS
        assert not re.search(r"\b[a-z]+_[a-z0-9_]+\b", texto), texto
        assert "habilidade nº" not in texto


def test_agrupado_por_secao_com_essenciais_primeiro():
    resultado = _montar({"anoEscolar": "2º Ano"})
    titulos = [g["titulo"] for g in resultado["grupos"]]
    assert titulos[:4] == ["Identificação e escola", "Gestação e parto", "Desenvolvimento", "Histórico clínico e queixas"]
    essenciais = [g["essencial"] for g in resultado["grupos"]]
    assert essenciais == sorted(essenciais, reverse=True)  # nenhum essencial depois de um opcional
    gestacao = _grupo(resultado, "gestacao")
    assert all(i["essencial"] for i in gestacao["itens"])  # descrições "(se Sim)" só aparecem com Sim


def test_escala_so_entra_se_aplicada():
    sem_pdf = _montar()
    assert _grupo(sem_pdf, "escala_tod") is None
    assert {"chave": "tod", "titulo": "TOD"} in sem_pdf["escalas_para_adicionar"]

    assert _grupo(_montar(tipos=["tod"]), "escala_tod") is not None  # PDF da escala lido
    assert _grupo(_montar({"tod_0": "1"}), "escala_tod") is not None  # algum item preenchido pela IA
    assert _grupo(_montar(adicionadas=["tod"]), "escala_tod") is not None  # "Também apliquei"


def test_itens_da_ata_viram_uma_pendencia_so():
    resultado = _montar(tipos=["ata"])
    ata = _grupo(resultado, "escala_ata")
    assert ata["titulo"] == "Pontuações da ATA" and ata["escala"]
    assert ata["pendentes"] == 22  # os percentuais da tabela são opcionais
    sem_escala = _montar()
    assert resultado["essenciais"]["total"] == sem_escala["essenciais"]["total"] + 1  # a escala conta 1


def test_habilidades_com_o_nome_real_do_ano_escolar():
    habilidades = _grupo(_montar({"anoEscolar": "2º Ano"}), "habilidades")
    assert habilidades["titulo"] == "Habilidades acadêmicas do 2º Ano"
    assert habilidades["itens"][0]["rotulo"] == "Leitura De Palavras"
    assert _grupo(_montar(), "habilidades") is None  # sem ano escolar, nada a perguntar


def test_descricao_so_quando_a_resposta_e_sim_e_pares_ano_mes_juntos():
    rotulos = [i["chave"] for i in _grupo(_montar({"complicacaoParto": "Sim"}), "gestacao")["itens"]]
    assert "complicacaoPartoDescricao" in rotulos
    assert "complicacaoPartoDescricao" not in [i["chave"] for i in _grupo(_montar({"complicacaoParto": "Não"}), "gestacao")["itens"]]

    andou = next(i for i in _grupo(_montar(), "desenvolvimento")["itens"] if i["chave"] == "andouAno")
    assert [c["id"] for c in andou["campos"]] == ["andouAno", "andouMes"]


def test_dispensado_e_preenchido_contam_no_progresso():
    antes = _montar()
    depois = _montar(
        dados={
            "parto": {"valor": "Cesáreo", "situacao": "preenchido"},
            "sofrimentoFetal": {"valor": None, "situacao": "nao_informado"},
        }
    )
    assert depois["essenciais"]["resolvidos"] == antes["essenciais"]["resolvidos"] + 2
    parto = next(i for i in _grupo(depois, "gestacao")["itens"] if i["chave"] == "parto")
    assert parto["valores"] == {"parto": "Cesáreo"} and parto["situacao"] == "preenchido"


def test_campo_ja_respondido_no_laudo_nao_e_pendencia():
    assert "parto" not in [i["chave"] for i in _grupo(_montar({"parto": "Normal"}), "gestacao")["itens"]]


def test_sugestao_de_anexo_aparece_no_item_ate_ser_confirmada():
    sugestao = {"campo_id": "parto", "valor": "Cesáreo", "anexo_id": "a1", "anexo_nome": "ficha.jpg"}
    parto = next(i for i in _grupo(_montar(sugestoes=[sugestao]), "gestacao")["itens"] if i["chave"] == "parto")
    assert parto["sugestoes"] == [sugestao]
    confirmado = _montar(dados={"parto": {"valor": "Cesáreo", "situacao": "preenchido"}}, sugestoes=[sugestao])
    assert next(i for i in _grupo(confirmado, "gestacao")["itens"] if i["chave"] == "parto")["sugestoes"] == []


def test_essenciais_iguais_aos_do_formulario():
    """Mesmos essenciais da tela de fases do formulário (REGRAS)."""
    html = (RAIZ / "frontend" / "public" / "formulario-novo-paciente.html").read_text(encoding="utf-8")
    for secao, titulo in [("gestacao", "Anamnese Inicial"), ("desenvolvimento", "Histórico De Desenvolvimento Da Criança"),
                          ("historico", "Encaminhamento, Histórico E Queixas"), ("identificacao", "Identificação Do Paciente")]:
        linha = re.search(rf'"{re.escape(titulo)}": {{ campos: \[([^\]]*)\]', html).group(1)
        do_formulario = {c for c in re.findall(r'"(\w+)"', linha) if c in IDS}
        nossos = next(s for s in SECOES if s.chave == secao).essenciais
        assert do_formulario <= nossos, (secao, do_formulario - nossos)


# --- rotas --------------------------------------------------------------------


@pytest.fixture
def laudo(client):
    headers = registrar_e_logar(client)
    pid = client.post("/api/patients", json={"name": "Criança Teste", "birth_date": "2019-02-10"}, headers=headers).json()["id"]
    template = client.post("/api/templates/custom-form-avaliacao", headers=headers).json()
    with client.db_session_factory() as db:
        report = Report(
            patient_id=UUID(pid),
            template_id=UUID(template["id"]),
            answers_json={"anoEscolar": "2º Ano"},
            computed_json={"origem": "ia_pdf", "documentos": [{"tipo": "ata"}], "catalogo": CATALOGO_DADOS},
        )
        db.add(report)
        db.commit()
        return headers, pid, str(report.id)


def test_rota_devolve_as_pendencias(client, laudo):
    headers, _, rid = laudo
    resposta = client.get(f"/api/reports/{rid}/pendencias", headers=headers)
    assert resposta.status_code == 200
    assert _grupo(resposta.json(), "escala_ata")["pendentes"] == 22


def test_tambem_apliquei_adiciona_a_escala(client, laudo):
    headers, _, rid = laudo
    resposta = client.put(f"/api/reports/{rid}/escalas-aplicadas", json={"escalas": ["tod"]}, headers=headers)
    assert _grupo(resposta.json(), "escala_tod") is not None
    assert client.put(f"/api/reports/{rid}/escalas-aplicadas", json={"escalas": ["inventada"]}, headers=headers).status_code == 400


def test_laudo_antigo_sem_catalogo_recebe_o_do_formulario(client, laudo):
    headers, _, rid = laudo
    with client.db_session_factory() as db:
        report = db.get(Report, UUID(rid))
        report.computed_json = {"origem": "ia_pdf"}
        db.commit()
    assert client.get(f"/api/reports/{rid}/pendencias", headers=headers).status_code == 409
    assert client.post(f"/api/reports/{rid}/pendencias", json=CATALOGO_DADOS, headers=headers).status_code == 200
    assert client.get(f"/api/reports/{rid}/pendencias", headers=headers).status_code == 200


def test_outra_psicologa_nao_ve_as_pendencias(client, laudo):
    _, _, rid = laudo
    outra = registrar_e_logar(client, email="outra@exemplo.com")
    assert client.get(f"/api/reports/{rid}/pendencias", headers=outra).status_code == 404
    assert client.post(f"/api/reports/{rid}/pendencias", json=CATALOGO_DADOS, headers=outra).status_code == 404
    assert client.put(f"/api/reports/{rid}/escalas-aplicadas", json={"escalas": []}, headers=outra).status_code == 404


# --- dados complementares (salvamento automático) --------------------------------


def test_salvamento_mescla_por_campo_e_aparece_nas_pendencias(client, laudo):
    headers, pid, rid = laudo
    url = f"/api/patients/{pid}/dados-complementares"
    client.patch(url, json={"campos": {"parto": {"valor": "Cesáreo", "situacao": "preenchido"}}}, headers=headers)
    resposta = client.patch(url, json={"campos": {"sofrimentoFetal": {"situacao": "nao_informado"}}}, headers=headers)
    dados = resposta.json()["dados"]
    assert dados["parto"]["valor"] == "Cesáreo" and dados["sofrimentoFetal"]["situacao"] == "nao_informado"
    assert "atualizado_em" in dados["parto"]

    gestacao = _grupo(client.get(f"/api/reports/{rid}/pendencias", headers=headers).json(), "gestacao")
    parto = next(i for i in gestacao["itens"] if i["chave"] == "parto")
    assert parto["valores"]["parto"] == "Cesáreo" and parto["situacao"] == "preenchido"

    # Desfazer: null apaga o campo.
    dados = client.patch(url, json={"campos": {"sofrimentoFetal": None}}, headers=headers).json()["dados"]
    assert "sofrimentoFetal" not in dados and "parto" in dados


def test_salvamento_valida_campos_e_anexos(client, laudo):
    headers, pid, _ = laudo
    url = f"/api/patients/{pid}/dados-complementares"
    assert client.patch(url, json={"campos": {"x y": {"situacao": "preenchido"}}}, headers=headers).status_code == 422
    assert client.patch(url, json={"campos": {"parto": {"situacao": "talvez"}}}, headers=headers).status_code == 422
    anexo_alheio = {"parto": {"valor": "Normal", "situacao": "preenchido", "origem": "anexo", "anexo_id": "00000000-0000-0000-0000-000000000001"}}
    assert client.patch(url, json={"campos": anexo_alheio}, headers=headers).status_code == 400


def test_outra_psicologa_nao_salva_dados_do_paciente(client, laudo):
    _, pid, _ = laudo
    outra = registrar_e_logar(client, email="outra@exemplo.com")
    resposta = client.patch(f"/api/patients/{pid}/dados-complementares", json={"campos": {}}, headers=outra)
    assert resposta.status_code == 404


# --- atualizar o laudo -----------------------------------------------------------

import app.api.pendencias as rotas_pendencias  # noqa: E402
import app.services.ai.agentes.extracao as extracao  # noqa: E402


@pytest.fixture
def ia_do_estudo(monkeypatch, client, laudo):
    headers, _, rid = laudo
    client.put("/api/settings/ai", json={"provider": "anthropic", "model": "claude-sonnet-5", "api_key": "chave-de-teste-1234"}, headers=headers)
    with client.db_session_factory() as db:
        report = db.get(Report, UUID(rid))
        report.answers_json = {**report.answers_json, "estudoCaso": "Estudo original da IA."}
        report.computed_json = {
            **report.computed_json,
            "estudo_de_caso_ia": "Estudo original da IA.",
            "documentos": [{"arquivo": "mae.pdf", "tipo": "formulario", "titulo": "Anamnese", "respostas": [{"pergunta": "Sono", "resposta": "Agitado"}]}],
        }
        db.commit()
    chamadas = []

    def redator(**kwargs):
        chamadas.append(kwargs)
        return "Estudo reescrito com os dados novos."

    def integrador(**kwargs):
        chamadas.append(kwargs)
        return "Estudo original da IA, agora com os dados novos."

    monkeypatch.setattr(rotas_pendencias, "redigir_estudo_de_caso", redator)
    monkeypatch.setattr(rotas_pendencias, "integrar_dados_ao_estudo_de_caso", integrador)
    # Atualizar nunca relê os PDFs.
    monkeypatch.setattr(extracao, "extrair_documento", lambda **kw: pytest.fail("releu um PDF"))
    return chamadas


def _confirmar(client, headers, pid, campos):
    client.patch(f"/api/patients/{pid}/dados-complementares", json={"campos": campos}, headers=headers)


def _atualizar(client, headers, rid, **corpo):
    resposta = client.post(f"/api/reports/{rid}/atualizar", json=corpo, headers=headers)
    assert resposta.status_code == 200, resposta.text
    resultado = resposta.json()
    if resultado["job_id"]:
        import time

        for _ in range(300):
            andamento = client.get(f"/api/laudo-ia/jobs/{resultado['job_id']}", headers=headers).json()
            if andamento["status"] in ("concluido", "erro"):
                resultado["andamento"] = andamento
                break
            time.sleep(0.01)
    return resultado, client.get(f"/api/reports/{rid}", headers=headers).json()


def test_aplica_os_campos_sem_ia_quando_nao_muda_o_estudo(client, laudo, ia_do_estudo):
    headers, pid, rid = laudo
    _confirmar(client, headers, pid, {
        "ata_item_0": {"valor": "2", "situacao": "preenchido"},
        "dom_atencao": {"valor": 35.0, "situacao": "preenchido"},
        "ata_item_1": {"situacao": "nao_se_aplica"},
    })
    resultado, laudo_atual = _atualizar(client, headers, rid)
    assert resultado == {"job_id": None, "campos_aplicados": 2, "estudo": "sem_mudanca"}
    assert laudo_atual["answers_json"]["ata_item_0"] == "2" and laudo_atual["answers_json"]["dom_atencao"] == "35"
    assert "ata_item_1" not in laudo_atual["answers_json"]  # dispensado não vai para o laudo
    assert not ia_do_estudo


def test_dados_de_gestacao_sao_incluidos_no_estudo_atual_sem_documentos(client, laudo, ia_do_estudo):
    headers, pid, rid = laudo
    _confirmar(client, headers, pid, {"parto": {"valor": "Cesáreo", "situacao": "preenchido"}})
    resultado, laudo_atual = _atualizar(client, headers, rid)
    assert resultado["estudo"] == "reescrevendo" and resultado["andamento"]["status"] == "concluido"
    assert laudo_atual["answers_json"]["parto"] == "Cesáreo"
    novo = "Estudo original da IA, agora com os dados novos."
    assert laudo_atual["answers_json"]["estudoCaso"] == novo
    assert laudo_atual["computed_json"]["estudo_de_caso_ia"] == novo
    assert laudo_atual["computed_json"]["estudo_campos_integrados"] == ["parto"]
    [chamada] = ia_do_estudo
    # Só o texto atual e o dado novo: os documentos do caso não são reenviados.
    assert chamada["estudo_atual"] == "Estudo original da IA."
    assert "Cesáreo" in chamada["dados_novos"] and "documentos_texto" not in chamada


def test_dado_ja_incluido_nao_volta_para_a_ia(client, laudo, ia_do_estudo):
    headers, pid, rid = laudo
    _confirmar(client, headers, pid, {"parto": {"valor": "Cesáreo", "situacao": "preenchido"}})
    _atualizar(client, headers, rid)
    resultado, _ = _atualizar(client, headers, rid)
    assert resultado == {"job_id": None, "campos_aplicados": 0, "estudo": "sem_mudanca"}
    assert len(ia_do_estudo) == 1


def test_estudo_editado_a_mao_e_mantido_salvo_pedido(client, laudo, ia_do_estudo):
    headers, pid, rid = laudo
    client.put(f"/api/reports/{rid}/answers", json={"answers": {"anoEscolar": "2º Ano", "estudoCaso": "Texto ajustado pela psicóloga."}}, headers=headers)
    _confirmar(client, headers, pid, {"parto": {"valor": "Normal", "situacao": "preenchido"}})
    assert client.get(f"/api/reports/{rid}/pendencias", headers=headers).json()["estudo_de_caso"] == {"editado": True}

    resultado, laudo_atual = _atualizar(client, headers, rid)
    assert resultado["estudo"] == "mantido_editado" and not ia_do_estudo
    assert laudo_atual["answers_json"]["estudoCaso"] == "Texto ajustado pela psicóloga."
    assert laudo_atual["answers_json"]["parto"] == "Normal"

    # A pedido, os dados novos entram no texto editado (que é a base).
    resultado, laudo_atual = _atualizar(client, headers, rid, reescrever_estudo=True)
    assert resultado["estudo"] == "reescrevendo" and len(ia_do_estudo) == 1
    assert ia_do_estudo[0]["estudo_atual"] == "Texto ajustado pela psicóloga."
    assert laudo_atual["answers_json"]["estudoCaso"] == "Estudo original da IA, agora com os dados novos."


def test_sem_estudo_anterior_redige_sobre_os_documentos_ja_lidos(client, laudo, ia_do_estudo):
    headers, pid, rid = laudo
    client.put(f"/api/reports/{rid}/answers", json={"answers": {"anoEscolar": "2º Ano", "estudoCaso": ""}}, headers=headers)
    _confirmar(client, headers, pid, {"parto": {"valor": "Cesáreo", "situacao": "preenchido"}})
    resultado, laudo_atual = _atualizar(client, headers, rid, reescrever_estudo=True)
    assert resultado["andamento"]["status"] == "concluido"
    [chamada] = ia_do_estudo
    assert '"titulo":"Anamnese"' in chamada["documentos_texto"] and "Cesáreo" in chamada["documentos_texto"]
    assert laudo_atual["answers_json"]["estudoCaso"] == "Estudo reescrito com os dados novos."


def test_dado_confirmado_nao_sobrescreve_resposta_do_laudo(client, laudo, ia_do_estudo):
    headers, pid, rid = laudo
    _confirmar(client, headers, pid, {"anoEscolar": {"valor": "5º Ano", "situacao": "preenchido"}})
    _, laudo_atual = _atualizar(client, headers, rid)
    assert laudo_atual["answers_json"]["anoEscolar"] == "2º Ano"


def test_outra_psicologa_nao_atualiza_o_laudo(client, laudo):
    _, _, rid = laudo
    outra = registrar_e_logar(client, email="outra@exemplo.com")
    assert client.post(f"/api/reports/{rid}/atualizar", json={}, headers=outra).status_code == 404


def test_remove_metodos_preservando_respostas_e_permite_reincluir(client, laudo):
    headers, _, rid = laudo
    with client.db_session_factory() as db:
        report = db.get(Report, UUID(rid))
        report.answers_json = {**report.answers_json, 'cars_0': '2'}
        db.commit()
    url = f'/api/reports/{rid}/metodos-excluidos'
    outra = registrar_e_logar(client, email='outra@example.com')
    assert client.put(url, json={'escalas': ['cars']}, headers=outra).status_code == 404
    assert client.put(url, json={'escalas': ['invalida']}, headers=headers).status_code == 400
    resultado = client.put(url, json={'escalas': ['ata', 'cars']}, headers=headers)
    assert resultado.status_code == 200
    assert _grupo(resultado.json(), 'escala_ata') is None
    assert _grupo(resultado.json(), 'escala_cars') is None
    assert not next(m for m in resultado.json()['metodos'] if m['chave'] == 'cars')['incluido']
    respostas = client.get(f'/api/reports/{rid}', headers=headers).json()['answers_json']
    assert respostas['cars_0'] == '2'
    assert respostas['__metodosExcluidos'] == ['ata', 'cars']
    resultado = client.put(url, json={'escalas': []}, headers=headers).json()
    assert _grupo(resultado, 'escala_cars') is not None
    assert _grupo(resultado, 'escala_ata') is not None
