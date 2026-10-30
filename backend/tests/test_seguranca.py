"""Testes das correções de segurança (auditoria de 2026-10-05)."""

from pathlib import Path

import pytest

import app.main as main_module
from app.core import rate_limit
from app.core.config import Settings
from tests.helpers import registrar_e_logar


@pytest.fixture
def frontend_dist_falso(tmp_path, monkeypatch):
    """Monta um frontend/dist de mentira e garante a rota de SPA."""
    dist = tmp_path / "frontend" / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>")
    (dist / "favicon.svg").write_text("<svg/>")
    (tmp_path / "segredo.env").write_text("JWT_SECRET=vazou")
    monkeypatch.setattr(main_module, "frontend_dist", dist)
    monkeypatch.setattr(main_module, "frontend_dist_resolvido", dist.resolve())
    return dist


@pytest.mark.parametrize(
    "caminho",
    [
        "/..%2f..%2fsegredo.env",
        "/%2e%2e/%2e%2e/segredo.env",
        "/..%2F..%2Fsegredo.env",
        "/....//....//segredo.env",
    ],
)
def test_rota_do_frontend_nao_le_arquivo_fora_do_dist(client, frontend_dist_falso, caminho):
    if not any(getattr(r, "path", "") == "/{full_path:path}" for r in main_module.app.routes):
        pytest.skip("frontend/dist não existe neste ambiente: rota de SPA não registrada")
    resposta = client.get(caminho)
    assert "vazou" not in resposta.text


def test_rota_do_frontend_ainda_serve_arquivos_do_dist(client, frontend_dist_falso):
    if not any(getattr(r, "path", "") == "/{full_path:path}" for r in main_module.app.routes):
        pytest.skip("frontend/dist não existe neste ambiente")
    assert client.get("/favicon.svg").text == "<svg/>"
    assert client.get("/pacientes").text == "<html>app</html>"


def test_arquivos_do_frontend_respondem_304_quando_nao_mudaram(client, frontend_dist_falso):
    if not any(getattr(r, "path", "") == "/{full_path:path}" for r in main_module.app.routes):
        pytest.skip("frontend/dist não existe neste ambiente")
    for caminho in ("/favicon.svg", "/pacientes"):
        primeira = client.get(caminho)
        assert primeira.status_code == 200 and primeira.headers["Cache-Control"] == "no-cache"
        etag = primeira.headers["ETag"]
        assert client.get(caminho, headers={"If-None-Match": etag}).status_code == 304
        # ETag como o Caddy devolve depois de comprimir (fraco e com sufixo).
        comprimido = "W/" + etag[:-1] + '-gzip"'
        assert client.get(caminho, headers={"If-None-Match": comprimido}).status_code == 304
        assert client.get(caminho, headers={"If-None-Match": '"outro"'}).status_code == 200


def test_producao_recusa_jwt_secret_fraco_ou_de_exemplo():
    for fraco in ("change-me", "troque-por-um-segredo-forte", "gere-com-openssl-rand-hex-32", "curto"):
        with pytest.raises(ValueError, match="JWT_SECRET"):
            Settings(env="production", jwt_secret=fraco, _env_file=None)
    assert Settings(env="production", jwt_secret="a" * 64, _env_file=None).em_producao


def test_cadastro_publico_fica_desligado_em_producao_por_padrao():
    forte = "b" * 64
    assert Settings(env="production", jwt_secret=forte, _env_file=None).cadastro_publico is False
    assert (
        Settings(env="production", jwt_secret=forte, allow_registration=True, _env_file=None).cadastro_publico is True
    )
    assert Settings(env="development", _env_file=None).cadastro_publico is True


def test_register_respeita_cadastro_desligado(client, monkeypatch):
    monkeypatch.setattr("app.api.auth.settings.allow_registration", False)
    resposta = client.post(
        "/api/auth/register", json={"name": "X", "email": "x@example.com", "password": "senhaSegura123"}
    )
    assert resposta.status_code == 403


def test_cabecalhos_de_seguranca(client):
    resposta = client.get("/api/health")
    assert resposta.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'self'" in resposta.headers["Content-Security-Policy"]
    assert "object-src 'none'" in resposta.headers["Content-Security-Policy"]
    assert resposta.headers["Cache-Control"] == "no-store"
    assert resposta.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_limite_de_login_por_ip_bloqueia_varios_emails_do_mesmo_lugar(client):
    for i in range(rate_limit.MAX_TENTATIVAS_POR_IP):
        client.post("/api/auth/login", json={"email": f"tentativa{i}@example.com", "password": "errada"})
    resposta = client.post("/api/auth/login", json={"email": "outro@example.com", "password": "errada"})
    assert resposta.status_code == 429
    assert "desta rede" in resposta.json()["detail"]


def test_upload_de_foto_grande_demais_e_recusado(client, tmp_path, monkeypatch):
    import app.core.uploads as uploads
    import app.services.storage as storage_module

    monkeypatch.setattr(storage_module, "_LOCAL_STORAGE_ROOT", tmp_path / "st")
    monkeypatch.setattr(uploads, "TAMANHO_MAXIMO_PADRAO", 10)
    monkeypatch.setattr(uploads.ler_upload, "__defaults__", (10,))
    headers = registrar_e_logar(client)
    pid = client.post("/api/patients", json={"name": "P", "birth_date": "2020-01-01"}, headers=headers).json()["id"]
    resposta = client.post(
        f"/api/patients/{pid}/photos", headers=headers, files={"file": ("f.jpg", b"x" * 11, "image/jpeg")}
    )
    assert resposta.status_code == 413


def test_pdf_nao_busca_arquivos_locais_do_servidor(tmp_path):
    from app.services.laudo_documento import html_para_pdf

    segredo = tmp_path / "segredo.txt"
    segredo.write_text("SEGREDO-DO-SERVIDOR")
    pdf = html_para_pdf(f'<p>oi</p><img src="file://{segredo}"><link rel="stylesheet" href="file://{segredo}">')
    assert pdf.startswith(b"%PDF")
    assert b"SEGREDO-DO-SERVIDOR" not in pdf


def test_pdf_legado_tambem_usa_buscador_seguro():
    fonte = Path("app/services/pdf.py").read_text()
    assert "HTML(string=html).write_pdf()" not in fonte
