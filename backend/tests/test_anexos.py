"""Anexos para completar o laudo: compressão, leitura pela IA (falsa),
sugestões validadas e controle de acesso."""

import io
import time

import pytest
from PIL import Image

import app.api.anexos as modulo
import app.services.storage as storage_module
from app.services.ai.agentes.anexos import CampoSugerido, LeituraDoAnexo
from app.services.imagens import ArquivoInvalido, imagens_para_ia, tipo_do_arquivo
from tests.helpers import registrar_e_logar
from tests.test_pendencias import _grupo, laudo  # noqa: F401 - fixture


@pytest.fixture(autouse=True)
def usar_storage_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_module, "_LOCAL_STORAGE_ROOT", tmp_path / "storage_teste")


def _foto(largura=3000, altura=2000, com_gps=True) -> bytes:
    imagem = Image.new("RGB", (largura, altura), (200, 180, 160))
    saida = io.BytesIO()
    exif = Image.Exif()
    if com_gps:
        exif[0x0110] = "Celular Fictício"  # modelo da câmera
        exif[0x8825] = {2: (23.0, 33.0, 0.0)}  # GPS
    imagem.save(saida, format="JPEG", exif=exif)
    return saida.getvalue()


# --- compressão -------------------------------------------------------------


def test_foto_reduzida_e_sem_metadados():
    original = _foto()
    [comprimida] = imagens_para_ia(original, "image/jpeg")
    imagem = Image.open(io.BytesIO(comprimida))
    assert max(imagem.size) == 1600
    assert not imagem.getexif()  # sem GPS, sem modelo da câmera
    assert len(comprimida) < len(original)


def test_tipo_do_arquivo_confere_o_conteudo():
    assert tipo_do_arquivo("ficha.JPG", _foto(10, 10)) == "image/jpeg"
    with pytest.raises(ArquivoInvalido):
        tipo_do_arquivo("ficha.jpg", b"%PDF-1.4 disfarcado")
    with pytest.raises(ArquivoInvalido):
        tipo_do_arquivo("planilha.xlsx", b"PK\x03\x04")


# --- rotas ------------------------------------------------------------------


def _configurar_ia(client, headers):
    client.put(
        "/api/settings/ai", json={"provider": "anthropic", "model": "claude-sonnet-5", "api_key": "chave-de-teste-1234"}, headers=headers
    )


def _esperar(client, headers, pid, rid):
    for _ in range(300):
        anexos = client.get(f"/api/patients/{pid}/anexos", params={"report_id": rid}, headers=headers).json()
        if all(a["status"] != "analisando" for a in anexos):
            return anexos
        time.sleep(0.01)
    raise AssertionError("a leitura não terminou")


@pytest.fixture
def ia_de_anexo(monkeypatch):
    chamadas = []

    def falsa(**kwargs):
        chamadas.append(kwargs)
        return LeituraDoAnexo(
            campos=[
                CampoSugerido(id="parto", valor="Cesáreo", trecho="parto cesárea"),
                CampoSugerido(id="idadeGestacional", valor="99 semanas"),  # fora das opções: descartado
                CampoSugerido(id="campo_inventado", valor="x"),  # fora do catálogo: descartado
                CampoSugerido(id="ata_item_0", valor="1"),  # fora da seção pedida: descartado
            ]
        )

    monkeypatch.setattr(modulo, "ler_anexo", falsa)
    return chamadas


def test_foto_vira_sugestao_so_dos_campos_pendentes_da_secao(client, laudo, ia_de_anexo):  # noqa: F811
    headers, pid, rid = laudo
    _configurar_ia(client, headers)
    resposta = client.post(
        f"/api/patients/{pid}/anexos",
        headers=headers,
        files={"arquivo": ("ficha_anamnese.jpg", _foto(), "image/jpeg")},
        data={"report_id": rid, "secao": "gestacao"},
    )
    assert resposta.status_code == 202 and resposta.json()["status"] == "analisando"
    [anexo] = _esperar(client, headers, pid, rid)
    assert anexo["status"] == "pronto" and anexo["sugestoes"] == 1

    # A IA recebeu imagem comprimida e só os campos que faltam na seção.
    chamada = ia_de_anexo[0]
    assert max(Image.open(io.BytesIO(chamada["imagens"][0])).size) <= 1600
    assert "[parto]" in chamada["catalogo_texto"] and "[ata_item_0]" not in chamada["catalogo_texto"]

    pendencias = client.get(f"/api/reports/{rid}/pendencias", headers=headers).json()
    parto = next(i for i in _grupo(pendencias, "gestacao")["itens"] if i["chave"] == "parto")
    assert parto["sugestoes"] == [
        {"campo_id": "parto", "valor": "Cesáreo", "trecho": "parto cesárea", "anexo_id": anexo["id"], "anexo_nome": "ficha_anamnese.jpg"}
    ]
    # Nada entra no laudo sem confirmação.
    laudo_atual = client.get(f"/api/reports/{rid}", headers=headers).json()
    assert "parto" not in laudo_atual["answers_json"]


def test_falha_da_ia_vira_mensagem_no_anexo(client, laudo, monkeypatch):  # noqa: F811
    headers, pid, rid = laudo
    _configurar_ia(client, headers)

    class Timeout(Exception):
        pass

    monkeypatch.setattr(modulo, "ler_anexo", lambda **kw: (_ for _ in ()).throw(Timeout("Request timed out.")))
    client.post(f"/api/patients/{pid}/anexos", headers=headers, files={"arquivo": ("ficha.jpg", _foto(), "image/jpeg")}, data={"report_id": rid})
    [anexo] = _esperar(client, headers, pid, rid)
    assert anexo["status"] == "erro" and "'ficha.jpg' (o provedor de IA demorou demais para responder)" in anexo["erro"]


def test_rejeita_arquivo_que_nao_e_foto_nem_pdf(client, laudo, ia_de_anexo):  # noqa: F811
    headers, pid, rid = laudo
    _configurar_ia(client, headers)
    resposta = client.post(
        f"/api/patients/{pid}/anexos", headers=headers, files={"arquivo": ("virus.exe", b"MZ\x90", "application/octet-stream")}, data={"report_id": rid}
    )
    assert resposta.status_code == 400
    assert not ia_de_anexo


def test_outra_psicologa_nao_acessa_os_anexos(client, laudo, ia_de_anexo):  # noqa: F811
    headers, pid, rid = laudo
    _configurar_ia(client, headers)
    client.post(f"/api/patients/{pid}/anexos", headers=headers, files={"arquivo": ("ficha.jpg", _foto(), "image/jpeg")}, data={"report_id": rid})
    [anexo] = _esperar(client, headers, pid, rid)

    outra = registrar_e_logar(client, email="outra@exemplo.com")
    _configurar_ia(client, outra)
    base = f"/api/patients/{pid}/anexos"
    assert client.get(base, headers=outra).status_code == 404
    assert client.get(f"{base}/{anexo['id']}/arquivo", headers=outra).status_code == 404
    assert client.delete(f"{base}/{anexo['id']}", headers=outra).status_code == 404
    envio = client.post(base, headers=outra, files={"arquivo": ("f.jpg", _foto(), "image/jpeg")}, data={"report_id": rid})
    assert envio.status_code == 404

    # A dona continua acessando e pode apagar.
    assert client.get(f"{base}/{anexo['id']}/arquivo", headers=headers).headers["content-type"] == "image/jpeg"
    assert client.delete(f"{base}/{anexo['id']}", headers=headers).status_code == 204
    assert client.get(base, headers=headers).json() == []
