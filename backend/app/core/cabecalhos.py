"""Cabeçalhos de segurança em todas as respostas (valem com ou sem o
Caddy na frente — ver docker-compose*.yml)."""

from fastapi import FastAPI, Request

# 'unsafe-inline' em script/style: o protocolo padrão
# (formulario-novo-paciente.html) é um HTML autocontido com scripts e
# estilos embutidos. Mesmo assim a política impede carregar scripts de
# outros domínios e enviar dados para fora (connect-src 'self').
CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self' data:",
        "connect-src 'self' data: blob:",
        "frame-src 'self' blob:",
        "frame-ancestors 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ]
)

CABECALHOS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    # SAMEORIGIN (não DENY): o Novo Atendimento embute o protocolo padrão
    # num <iframe> do próprio sistema.
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


def registrar_cabecalhos_de_seguranca(app: FastAPI) -> None:
    @app.middleware("http")
    async def _cabecalhos(request: Request, call_next):
        resposta = await call_next(request)
        for nome, valor in CABECALHOS.items():
            resposta.headers.setdefault(nome, valor)
        # Respostas da API têm dados de paciente: não guardar em cache.
        if request.url.path.startswith("/api/"):
            resposta.headers.setdefault("Cache-Control", "no-store")
        return resposta
