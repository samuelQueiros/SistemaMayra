# DEPLOY.md — Colocar o sistema no ar numa VPS

Passo a passo para subir o sistema numa VPS própria (Ubuntu/Debian) com
Docker Compose: **Postgres + aplicação + Caddy (HTTPS automático)**.
Revisado após a auditoria de segurança de 2026-10-05 (ver `ENTREGAS.md`).

> **Já existe uma versão no ar?** A versão anterior tinha uma falha que
> permitia baixar arquivos do servidor (incluindo o `.env` e o banco SQLite
> de desenvolvimento) sem login. Depois de atualizar, faça a
> [seção 7 — Se já havia uma versão no ar](#7-se-já-havia-uma-versão-no-ar).

## 1. Antes de começar

- VPS com **2 GB de RAM** ou mais (a geração de PDF e o build usam memória),
  Ubuntu 22.04/24.04 ou Debian 12.
- Um **domínio** (ex.: `laudos.suaclinica.com.br`) com registro **DNS tipo
  A** apontando para o IP da VPS. Confira com `dig +short SEU_DOMINIO`
  antes de subir — o certificado HTTPS só sai com o DNS já certo.
- Acesso SSH à VPS com um usuário que tenha `sudo`.

## 2. Preparar a VPS (uma vez)

```bash
# Atualizações e firewall: só SSH, HTTP e HTTPS abertos
sudo apt update && sudo apt upgrade -y
sudo apt install -y ufw git openssl
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
sudo ufw enable

# Atualizações de segurança automáticas do sistema
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Docker + plugin compose (script oficial)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"   # saia e entre de novo no SSH depois disso
```

Recomendado também: entrar no SSH só com chave (desligar senha em
`/etc/ssh/sshd_config`: `PasswordAuthentication no`) e instalar
`fail2ban` (`sudo apt install -y fail2ban`).

> Atenção: o Docker publica portas **por fora** do `ufw`. Por isso o
> `docker-compose.yml` só publica as portas 80/443 do Caddy — o app
> (8000) e o Postgres (5432) ficam só na rede interna do Docker. Não
> adicione `ports:` neles.

## 3. Instalar o sistema

```bash
sudo mkdir -p /opt/psicologa && sudo chown "$USER" /opt/psicologa
git clone <URL-DO-SEU-REPOSITORIO> /opt/psicologa
cd /opt/psicologa

# Gera o .env com segredos aleatórios fortes e a senha inicial da psicóloga
./scripts/gerar-env.sh

# Sobe tudo (build da imagem + Postgres + Caddy)
docker compose up -d --build

# Acompanhe até aparecer "certificate obtained successfully" no Caddy
docker compose logs -f caddy
```

Abra `https://SEU_DOMINIO` e entre com o e-mail e a senha mostrados pelo
`gerar-env.sh`. Depois, em **Configurações → Inteligência Artificial**,
escolha o provedor e cole a chave de API (ela fica criptografada no banco).

O que o `.env` gerado já traz:

| Variável | Valor | Por quê |
|---|---|---|
| `ENV` | `production` | Liga as proteções de produção (abaixo). |
| `JWT_SECRET` | 64 caracteres aleatórios | Assina os logins e criptografa as chaves de IA. **O sistema se recusa a subir em produção com um segredo fraco ou de exemplo.** |
| `POSTGRES_PASSWORD` | aleatória | Senha do banco (só acessível dentro do Docker). |
| `ADMIN_NAME` / `ADMIN_EMAIL` / `ADMIN_PASSWORD` | o que você informou / senha aleatória | Conta da psicóloga, criada/atualizada a cada start. Para trocar a senha: edite `ADMIN_PASSWORD` e rode `docker compose up -d`. |
| `ALLOW_REGISTRATION` | `false` | Ninguém consegue criar conta pela internet. |
| `JWT_EXPIRES_MINUTES` | `720` (12 h) | Validade do login. |

O `.env` fica com permissão `600` (só o seu usuário lê). Nunca o commite
nem envie por e-mail/WhatsApp.

## 4. Backups (obrigatório — dados de saúde, LGPD)

```bash
./scripts/backup.sh          # banco + arquivos enviados → ./backups/
```

Agende todo dia às 3h (`crontab -e`):

```
0 3 * * * cd /opt/psicologa && ./scripts/backup.sh >> backups/backup.log 2>&1
```

Mantém os 14 últimos. **Copie os backups para fora da VPS** (outro
servidor, Drive, S3…) — um backup só na própria VPS some junto com ela.
Teste a restauração pelo menos uma vez (seção 6).

## 5. Atualizar o sistema

```bash
cd /opt/psicologa
./scripts/atualizar.sh   # backup → git pull → rebuild → confere a saúde do app
```

As migrations do banco rodam sozinhas no start do container.

## 6. Restaurar um backup

```bash
cd /opt/psicologa
gunzip -c backups/banco_AAAAMMDD_HHMMSS.sql.gz | docker compose exec -T db psql -U formpsico formpsico
docker compose exec -T app sh -c 'rm -rf /app/backend/storage/*'
docker compose exec -T app tar -C /app/backend -xzf - < backups/arquivos_AAAAMMDD_HHMMSS.tar.gz
docker compose restart app
```

## 7. Se já havia uma versão no ar

A versão anterior permitia ler arquivos do servidor pela URL, sem login.
Depois de atualizar (`./scripts/atualizar.sh`):

1. **Troque o `JWT_SECRET`** (`openssl rand -hex 32`) no `.env` e rode
   `docker compose up -d`. Todos precisarão entrar de novo. As chaves de IA
   salvas ficam ilegíveis (eram criptografadas com o segredo antigo):
   **cadastre a chave de IA de novo** em Configurações.
2. **Troque o `ADMIN_PASSWORD`** e as **chaves de API** dos provedores de
   IA que estavam no `.env` do servidor (gere novas no painel de cada
   provedor e apague as antigas).
3. A senha do Postgres só era usada dentro do Docker; troque-a se quiser
   ficar 100% seguro (exige recriar o banco a partir de um backup).
4. **Imagem Docker publicada (GHCR):** as imagens antigas podiam conter o
   `backend/.env` e um backup do banco de desenvolvimento. Se o pacote no
   GitHub for **público**, torne-o privado e apague as versões antigas em
   GitHub → Packages.
5. **Pasta de arquivos enviados:** o container agora roda sem ser root. Se
   os arquivos já existiam, ajuste o dono uma vez:
   `docker compose run --rm --user root app chown -R 10001:10001 /app/backend/storage`

## 8. Proteções de segurança ativas

- Rota do frontend só serve arquivos de `frontend/dist` (corrigido o
  *path traversal*).
- Em produção: sem cadastro público, sem documentação da API (`/docs`),
  segredo JWT forte obrigatório.
- Login: bloqueio após 5 erros por e-mail ou 20 por IP em 15 minutos;
  tempo de resposta igual para e-mail existente ou não.
- Cabeçalhos: CSP (só recursos do próprio domínio), HSTS, `nosniff`,
  `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy`, `Permissions-Policy`,
  `Cache-Control: no-store` na API.
- PDFs gerados nunca buscam arquivos do servidor nem URLs externas.
- Uploads limitados (15 MB por arquivo; 100 MB por requisição no Caddy).
- Container sem root; imagem sem `.env`, bancos ou backups
  (`.dockerignore`).
- Chart.js e fontes servidos pelo próprio sistema (sem CDN de terceiros).
- Dependências sem vulnerabilidades conhecidas (`pip-audit` e `npm audit`
  em 2026-10-05). Rode de novo de tempos em tempos:
  `cd backend && pip install pip-audit && pip-audit -r requirements.txt`.
- Chaves de IA criptografadas no banco; senhas com bcrypt; cada psicóloga
  só acessa os próprios dados.

## 9. Alternativa: Portainer

Se a VPS usa Portainer, use `docker-compose.portainer.yml` (imagem
publicada no GHCR pelo GitHub Actions) com as variáveis de
`portainer.env.example`. Mesmas regras: `ENV=production`, `JWT_SECRET`
forte (`openssl rand -hex 32`), `ALLOW_REGISTRATION=false`, e os backups da
seção 4 (troque `docker compose exec` por `docker exec <container>`).
Deixe o pacote do GHCR **privado** (dados de saúde: a imagem não contém
dados, mas não há motivo para ser pública).
