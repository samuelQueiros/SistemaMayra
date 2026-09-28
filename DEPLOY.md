# DEPLOY.md — Checklist de implantação

Este arquivo é o roteiro para colocar o sistema no ar. Ninguém deve pular
um item sem anotar por quê. Nada aqui foi executado em produção — é só a
preparação (Prompt 4.4 do PROMPTS.md).

## 1. Variáveis de ambiente obrigatórias

Copie `.env.example` e preencha de verdade antes de subir o serviço
(local, com Docker, ou na plataforma de hospedagem escolhida):

| Variável | O que é | Observação |
|---|---|---|
| `ENV` | `production` em produção | Usado só como referência; não muda comportamento hoje. |
| `DATABASE_URL` | Conexão com o Postgres | Formato `postgresql+psycopg://usuario:senha@host:5432/banco`. Nunca usar SQLite em produção (CLAUDE.md seção 2 permite SQLite só em dev local). |
| `JWT_SECRET` | Segredo para assinar o login | **Trocar o valor de exemplo.** Gerar algo aleatório e forte (ex.: `openssl rand -hex 32`). Se vazar, qualquer um pode forjar login de qualquer psicóloga. |
| `JWT_ALGORITHM` | Algoritmo do token | Manter `HS256` (padrão já testado). |
| `JWT_EXPIRES_MINUTES` | Validade do login | Ajustar conforme a política da clínica (hoje: 1440 = 24h). |
| `AI_PROVIDER` | `anthropic` ou `openai` | Ver SPEC.md seção 5. |
| `AI_MODEL` | Nome do modelo | Ex.: `claude-sonnet-5`. |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Chave do provedor de IA escolhido | Sem isso, a geração de texto por IA falha com erro claro (não trava o resto do sistema). |
| `S3_BUCKET` | Nome do bucket (opcional) | Sem preencher, fotos/PDFs ficam em disco local do servidor (`backend/storage/`) — funciona, mas some se o disco não for persistente entre deploys/reinícios. Preenchendo, passam a ir para um bucket compatível com S3. |
| `S3_ENDPOINT_URL` | Endpoint do provedor (opcional) | Só necessário para provedores que não sejam a AWS S3 "de verdade" — ex.: Cloudflare R2, Backblaze B2, MinIO. Deixe vazio para AWS S3. |
| `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | Credenciais do bucket (opcional) | Geradas no painel do provedor escolhido. |

## 2. Banco de dados (Postgres)

- [ ] Banco Postgres criado e acessível a partir de onde o serviço vai
      rodar.
- [ ] Rodar as migrations antes do primeiro uso (o `Dockerfile` já faz
      isso automaticamente todo start: `alembic upgrade head`).
- [ ] Backup automático configurado — dados de pacientes/laudos são dados
      de saúde (LGPD, CLAUDE.md seção 5); perder isso é um problema sério,
      não só um inconveniente técnico. Use `backend/scripts/backup_db.sh`
      (faz um `pg_dump` compactado) agendado via cron, ou o backup
      gerenciado da própria plataforma de hospedagem, se houver (Render/
      Railway oferecem no plano pago). Exemplo de cron diário às 3h:
      `0 3 * * * DATABASE_URL="..." /caminho/backend/scripts/backup_db.sh /backups/$(date +\%F).sql.gz`
- [ ] Se for guardar fotos/PDFs em disco local (sem configurar
      `S3_BUCKET`), confirme que o volume onde `backend/storage/` vive é
      persistente entre deploys/reinícios — em muitas plataformas o disco
      é apagado a cada novo deploy. Se não for, configure `S3_BUCKET` (ver
      seção 1) para um bucket compatível com S3.

## 3. Build e implantação

- [x] `docker build -t formpsico .` a partir da raiz do projeto (o
      `Dockerfile` já compila o frontend e empacota tudo num único
      serviço, seguindo a decisão de arquitetura do CLAUDE.md seção 2).
      **Testado com sucesso em 2026-09-13** (build completo, sem erros).
- [x] Rodar com as variáveis de ambiente da seção 1, ex.:
      `docker run -p 8000:8000 --env-file .env formpsico`. **Testado com
      sucesso**: container sobe, roda as migrations sozinho, serve a API
      e o frontend na mesma porta.
- [x] Testado de ponta a ponta dentro do container: cadastro de
      psicóloga, login, seed dos templates (CARS/ATA/SNAP-IV), criação de
      paciente, geração de laudo e **download de PDF** (confirma que as
      bibliotecas de sistema do WeasyPrint instaladas no `Dockerfile`
      funcionam corretamente dentro do container).

### 3.1 Runbook para uma VPS genérica (Docker Compose + Caddy)

`docker-compose.yml` e `Caddyfile` na raiz do projeto sobem os 3 serviços
juntos: Postgres, a aplicação e Caddy como proxy reverso com HTTPS
automático (Let's Encrypt) para o domínio configurado — não precisa
configurar TLS na mão.

Pré-requisito: um registro DNS tipo A do seu domínio (ex.:
`laudos.suaclinica.com.br`) apontando para o IP público da VPS, propagado
*antes* de subir o Caddy (senão a emissão do certificado falha).

Na VPS (Ubuntu/Debian; ajuste para outra distro):

```bash
# 1. Docker + Docker Compose, se ainda não tiver
curl -fsSL https://get.docker.com | sh

# 2. Copiar o projeto para a VPS (git clone do seu repositório, ou
#    `rsync`/`scp` a partir da sua máquina)
git clone <url-do-seu-repositorio> formpsico
cd formpsico

# 3. Configurar variáveis de ambiente
cp .env.example .env
nano .env   # preencha JWT_SECRET (openssl rand -hex 32), POSTGRES_PASSWORD,
            # DOMAIN, e a chave de IA se for usar geração por IA

# 4. Subir tudo (build da imagem + Postgres + Caddy)
docker compose up -d --build

# 5. Acompanhar os logs até o Caddy confirmar o certificado emitido
docker compose logs -f caddy
```

Depois disso o sistema fica em `https://SEU_DOMINIO`, com renovação de
certificado automática pelo Caddy. Para atualizar após um novo commit:
`git pull && docker compose up -d --build`.

- [ ] Executado numa VPS real (o checklist acima ainda não foi rodado
      fora deste ambiente de desenvolvimento — confirme cada passo ao
      subir pela primeira vez).

### 3.2 Deploy pelo Portainer

Arquivos usados: `docker-compose.portainer.yml` (a stack),
`portainer.env.example` (modelo das variáveis) e
`.github/workflows/docker-publish.yml` (publica a imagem).

A stack usa uma **imagem pronta** no GitHub Container Registry, em vez de
buildar no servidor, e não sobe Caddy — servidores com Portainer
normalmente já têm um proxy reverso (Traefik, Nginx Proxy Manager...) em
80/443.

**1. Publicar a imagem (uma vez, e depois automático)**

- Faça push na `master`: o GitHub Actions builda o `Dockerfile` e publica
  `ghcr.io/samuelqueiros/psicologa:latest` (e uma tag `sha-<commit>`).
  Acompanhe em GitHub > Actions.
- O pacote nasce **privado**. Ou torne público (GitHub > Packages >
  psicologa > Package settings > Change visibility), ou cadastre o
  registry no Portainer: *Registries > Add registry > Custom registry*,
  URL `ghcr.io`, usuário do GitHub e um Personal Access Token (classic)
  com escopo `read:packages`.

**2. Criar a stack**

- Portainer > *Stacks > Add stack*, nome ex.: `psicologa`.
- *Web editor*: cole o conteúdo de `docker-compose.portainer.yml`.
  (Alternativa: *Repository*, apontando para este repositório e
  *Compose path* `docker-compose.portainer.yml` — se o repo for privado,
  informe as credenciais do GitHub.)
- *Environment variables > Load variables from .env file*: carregue uma
  cópia preenchida de `portainer.env.example`. Obrigatórias:
  `POSTGRES_PASSWORD` e `JWT_SECRET` (`openssl rand -hex 32`). Se a porta
  8000 já estiver em uso no servidor, troque `APP_PORT`.
- *Deploy the stack*. O container `app` roda as migrations sozinho e fica
  `healthy` quando `/api/health` responde.

**3. HTTPS / domínio**

- No proxy reverso existente, crie o host do domínio (ex.:
  `laudos.suaclinica.com.br`) apontando para `http://IP_DO_SERVIDOR:APP_PORT`
  (ou para `app:8000`, se o proxy estiver na mesma rede Docker da stack),
  com certificado Let's Encrypt. Não exponha o app sem HTTPS (seção 4).
- Se não houver proxy nenhum no servidor, use o `docker-compose.yml` com
  Caddy da seção 3.1.

**4. Atualizar após um novo commit**

- Push na `master` → espere o Actions terminar → no Portainer, abra a
  stack e clique *Update the stack* marcando *Re-pull image and
  redeploy*. (Para fixar uma versão, use `APP_IMAGE=ghcr.io/samuelqueiros/psicologa:sha-<commit>`.)

- [x] Stack testada localmente com `docker compose -f
      docker-compose.portainer.yml` (2026-09-28): migrations aplicadas,
      container `healthy`, API e frontend respondendo.
- [ ] Executado num Portainer real.
- [ ] Backup: os dados ficam nos volumes `<stack>_db_data` e
      `<stack>_app_storage` — configure o backup (seção 2) apontando para
      o Postgres da stack.

## 4. HTTPS

- [x] Resolvido pelo runbook da seção 3.1 (Caddy com HTTPS automático) —
      única exigência é o DNS do domínio já apontando para a VPS antes de
      subir o `docker compose`. Alternativa equivalente: Nginx + certbot,
      ou o HTTPS gerenciado da própria plataforma de hospedagem, caso não
      use o `docker-compose.yml` deste repositório.
- [ ] Sem HTTPS, o token de login (JWT) trafega em texto puro pela rede —
      inaceitável para dados de saúde. Não colocar no ar sem isso.

## 5. Checklist de segurança antes de ir ao ar

(ver também `ENTREGAS.md`, entrada "Testes finais e revisão de
segurança", Prompt 4.3, para o detalhamento do que já foi revisado)

- [x] Toda rota de dados de paciente/laudo exige login (revisado).
- [x] Cada psicóloga só acessa os próprios pacientes/laudos/templates
      (revisado).
- [x] Senhas com hash (bcrypt), nunca em texto puro (revisado).
- [x] Exclusão de paciente com histórico de laudos é bloqueada (corrigido
      no Prompt 4.3).
- [x] Chave de IA de cada psicóloga fica criptografada no banco (não em
      texto puro) — ver `ENTREGAS.md`, "Bloco de segurança".
- [x] Login tem limite de tentativas (bloqueio temporário após 5 erradas
      em 15 minutos) — ver `ENTREGAS.md`, "Bloco de segurança".
- [ ] `JWT_SECRET` trocado para um valor forte e único de produção (não o
      do `.env.example`).
- [ ] HTTPS configurado (ver seção 4).
- [ ] Backup do banco de dados configurado (ver seção 2).
- [ ] Considerar, se o sistema for exposto publicamente: limite de
      tentativas de login (proteção contra força bruta) — não implementado
      ainda, fora da lista mínima do SPEC.md, mas recomendável.

## 6. Depois de subir

- [ ] Cadastrar a primeira conta de psicóloga (`POST /api/auth/register`).
- [ ] Nada mais a semear: desde 2026-09-20 o sistema usa um protocolo fixo
      (`frontend/public/formulario-novo-paciente.html`), não mais templates
      configuráveis por escala. O `ReportTemplate` interno
      (`rule_type="custom_form"`) é criado sozinho, de forma idempotente,
      na primeira vez que a psicóloga salvar um atendimento pelo
      formulário — não é preciso rodar `seed_templates` (ver `CLAUDE.md`
      seção 9).
