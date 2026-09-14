# Sistema de Relatório Automático para Psicólogos

Ver `CLAUDE.md` (contexto do projeto e decisões de arquitetura) e `SPEC.md`
(especificação técnica: entidades, endpoints, motor de regras, IA) antes de
mexer em qualquer parte do sistema.

## Arquitetura (resumo)

Um único serviço em produção: o backend FastAPI expõe a API REST **e** serve
os arquivos estáticos do build do frontend (`frontend/dist`). Não há
servidor Node em produção — Node só é usado para compilar o frontend.

## Como rodar em desenvolvimento

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # ajuste os valores conforme necessário
uvicorn app.main:app --reload
```

A API sobe em `http://localhost:8000`. Rota de verificação:
`GET /api/health`.

### Frontend (dev, com hot reload)

Em outro terminal, com o backend já rodando:

```bash
cd frontend
npm install
npm run dev
```

O Vite sobe em `http://localhost:5173` e faz proxy de `/api` para o backend
(ver `frontend/vite.config.ts`).

## Como rodar em modo produção (um único serviço)

```bash
cd frontend && npm install && npm run build
cd ../backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

O FastAPI detecta `frontend/dist` e passa a servir o frontend na raiz (`/`)
junto com a API (`/api/...`) na mesma porta.

## Migrations

```bash
cd backend
alembic upgrade head
```

## Docker (build único)

```bash
docker build -t formpsico .
docker run -p 8000:8000 --env-file backend/.env formpsico
```

Ver `DEPLOY.md` para o checklist completo de implantação (variáveis de
ambiente obrigatórias, banco de dados, HTTPS, segurança).

## Estrutura de pastas

Ver `CLAUDE.md` seção 3.

## Acompanhamento do projeto

O progresso de cada entrega é registrado em `ENTREGAS.md` — pensado para a
psicóloga acompanhar sem precisar ler código.
