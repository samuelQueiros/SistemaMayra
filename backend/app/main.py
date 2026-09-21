from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401 -- garante que todos os modelos sejam registrados no ORM
from app.api import ai_settings, auth, patients, reports, stats, templates

app = FastAPI(title="Sistema de Relatório Automático para Psicólogos")

app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(templates.router)
app.include_router(reports.router)
app.include_router(ai_settings.router)
app.include_router(stats.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Serve o build do frontend (frontend/dist) quando existir, no mesmo processo
# e porta da API (ver CLAUDE.md seção 2: um único serviço em produção).
# Precisa ser registrado por último: as rotas de API acima têm prioridade.
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # Rotas de API que não existem devem continuar dando 404 "de API",
        # não a página do frontend.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        candidate = frontend_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)

        # Fallback de SPA: qualquer outra rota (ex.: /dashboard, recarregada
        # direto no navegador) devolve o index.html e o React Router decide
        # o que mostrar no lado do cliente. Cache-Control: no-cache força o
        # navegador a sempre revalidar essa casca (que referencia o bundle
        # JS hasheado do build atual) em vez de reter uma versão antiga
        # depois de um novo deploy.
        return FileResponse(frontend_dist / "index.html", headers={"Cache-Control": "no-cache"})
