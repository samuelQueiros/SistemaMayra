"""Ponto de entrada do FastAPI: registra as rotas da API, os cabeçalhos de segurança, a compressão gzip
e, quando existe `frontend/dist`, serve o frontend na mesma porta (um único serviço em produção)."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.requests import Request
from starlette.responses import Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import DEFAULT_EXCLUDED_CONTENT_TYPES, GZipMiddleware

from app import models  # noqa: F401 -- garante que todos os modelos sejam registrados no ORM
from app.api import (
    ai_settings,
    anexos,
    auth,
    documents,
    guardian_forms,
    laudo_ia,
    patients,
    pendencias,
    protocolos,
    relatorios_pdf,
    reports,
    stats,
    templates,
)
from app.core.config import settings
from app.core.cabecalhos import registrar_cabecalhos_de_seguranca
from app.core.errors import registrar_tratadores_de_erro

# Documentação interativa da API (/docs, /redoc, /openapi.json) só fora de
# produção — em produção ela só ajudaria quem estiver sondando o sistema.
_docs = {} if not settings.em_producao else {"docs_url": None, "redoc_url": None, "openapi_url": None}
app = FastAPI(title="Sistema de Relatório Automático para Psicólogos", **_docs)
registrar_tratadores_de_erro(app)
registrar_cabecalhos_de_seguranca(app)

# Compressão no próprio app: a stack do Portainer usa `caddy reverse-proxy`,
# que não comprime (o formulário padrão cai de ~570 KB para ~270 KB). Atrás
# do Caddyfile com `encode gzip`, o Caddy repassa a resposta já comprimida.
# PDF e Word já são comprimidos (imagens e fontes já estão no padrão do
# Starlette): não vale gastar CPU com eles.
app.add_middleware(
    GZipMiddleware,
    minimum_size=1024,
    compresslevel=6,
    exclude_content_types=(
        *DEFAULT_EXCLUDED_CONTENT_TYPES,
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
)

app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(templates.router)
app.include_router(protocolos.router)
app.include_router(relatorios_pdf.router)
app.include_router(laudo_ia.router)
app.include_router(pendencias.router)
app.include_router(anexos.router)
app.include_router(reports.router)
app.include_router(ai_settings.router)
app.include_router(stats.router)
app.include_router(documents.router)
app.include_router(guardian_forms.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Verificação de saúde usada pelo HEALTHCHECK do Docker e pelo `scripts/atualizar.sh`."""
    return {"status": "ok"}


# Serve o build do frontend (frontend/dist) quando existir, no mesmo processo
# e porta da API (ver CLAUDE.md seção 2: um único serviço em produção).
# Precisa ser registrado por último: as rotas de API acima têm prioridade.
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"

frontend_dist_resolvido = frontend_dist.resolve()


class ArquivosComHash(StaticFiles):
    """/assets do build do Vite: o nome muda a cada build (hash), então o
    navegador pode guardar por um ano sem revalidar."""

    async def get_response(self, path, scope):
        resposta = await super().get_response(path, scope)
        if resposta.status_code in (200, 304):
            resposta.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resposta


def _etag_sem_compressao(etag: str) -> str:
    # O Caddy (encode gzip) marca o ETag como fraco e/ou com sufixo "-gzip".
    etag = etag.strip().removeprefix("W/")
    for sufixo in ("-gzip", "-zstd", "-br"):
        etag = etag.replace(sufixo + '"', '"')
    return etag


def _arquivo_revalidado(request: Request, caminho: Path) -> Response:
    """Arquivos sem hash no nome (index.html, formulário, Chart.js, imagens
    do laudo): o navegador revalida a cada uso e recebe 304 sem corpo
    quando nada mudou — sempre a versão do último deploy, sem baixar de novo."""
    info = caminho.stat()
    etag = f'"{info.st_mtime_ns:x}-{info.st_size:x}"'
    cabecalhos = {"ETag": etag, "Cache-Control": "no-cache"}
    pedido = request.headers.get("if-none-match", "")
    if pedido and any(_etag_sem_compressao(e) == etag for e in pedido.split(",")):
        return Response(status_code=304, headers=cabecalhos)
    return FileResponse(caminho, headers=cabecalhos, stat_result=info)


if frontend_dist.exists():
    app.mount("/assets", ArquivosComHash(directory=frontend_dist / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str, request: Request):
        """Entrega arquivos do build do frontend e, para qualquer outra rota, o `index.html` (o React Router
        decide a tela). Só serve arquivos de dentro de `frontend/dist` (proteção contra path traversal)."""
        # Rotas de API que não existem devem continuar dando 404 "de API",
        # não a página do frontend.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        # resolve() + is_relative_to(): só arquivos de DENTRO de frontend/dist.
        # Sem isso, "/..%2f..%2fbackend%2f.env" lia qualquer arquivo do
        # servidor (path traversal).
        candidate = (frontend_dist / full_path).resolve()
        if full_path and candidate.is_relative_to(frontend_dist_resolvido) and candidate.is_file():
            return _arquivo_revalidado(request, candidate)

        # Fallback de SPA: qualquer outra rota (ex.: /dashboard, recarregada
        # direto no navegador) devolve o index.html e o React Router decide
        # o que mostrar no lado do cliente. Cache-Control: no-cache força o
        # navegador a sempre revalidar essa casca (que referencia o bundle
        # JS hasheado do build atual) em vez de reter uma versão antiga
        # depois de um novo deploy.
        return _arquivo_revalidado(request, frontend_dist / "index.html")
