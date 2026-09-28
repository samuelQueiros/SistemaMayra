# Build do frontend (Node só é usado aqui — nunca em produção/runtime,
# ver CLAUDE.md seção 2).
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Serviço único de produção: backend FastAPI servindo a API e o build do
# frontend na mesma porta.
FROM python:3.12-slim AS backend
WORKDIR /app/backend

# Bibliotecas de sistema exigidas pelo WeasyPrint (geração de PDF) e por
# fontes usadas na renderização.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        shared-mime-info \
        fonts-dejavu-core \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Usado pelo Docker/Portainer para mostrar o container como "healthy".
# python:slim não tem curl, então a checagem usa o próprio Python.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)" || exit 1

# Aplica migrations pendentes e sobe o serviço. Variáveis de ambiente
# (DATABASE_URL, JWT_SECRET, ANTHROPIC_API_KEY, ...) vêm de fora do
# container (docker run -e / docker-compose / secrets da plataforma) —
# ver DEPLOY.md. --proxy-headers faz o app enxergar https/IP real quando
# roda atrás de proxy reverso (Caddy, Traefik, Nginx Proxy Manager).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers '--forwarded-allow-ips=*'"]
