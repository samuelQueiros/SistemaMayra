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

## 4. HTTPS

- [ ] O serviço roda hoje só em HTTP simples (`uvicorn`), sem HTTPS
      embutido. Em produção, colocar atrás de um proxy reverso (ex.:
      Caddy, Nginx, ou o HTTPS gerenciado da própria plataforma de
      hospedagem) que termine o TLS e encaminhe para a porta 8000 do
      container.
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
- [ ] Cadastrar os modelos de laudo reais (CARS, ATA, SNAP-IV) via
      `python -m app.seed_templates <email>` (dentro do container, ou
      apontando `DATABASE_URL` para o banco de produção a partir de uma
      máquina com acesso) — **lembrando que o modelo da ATA está
      incompleto** (ver `TEMPLATES_LAUDOS.md` e a entrega do Prompt 2.3b em
      `ENTREGAS.md`) e precisa ser revisado pela psicóloga antes do
      primeiro uso clínico real.
