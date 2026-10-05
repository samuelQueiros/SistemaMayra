#!/usr/bin/env bash
# Gera o .env de produção para o docker-compose.yml, com segredos
# aleatórios fortes. Uso (na VPS, na pasta do projeto):
#   ./scripts/gerar-env.sh
# Não sobrescreve um .env existente.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then
  echo "Já existe um .env aqui. Apague-o (ou renomeie) se quiser gerar outro." >&2
  exit 1
fi

aleatorio() { openssl rand -hex "$1"; }

read -rp "Domínio do sistema (ex.: laudos.suaclinica.com.br): " DOMINIO
read -rp "Nome da psicóloga (login): " ADMIN_NOME
read -rp "E-mail de login da psicóloga: " ADMIN_EMAIL
SENHA_ADMIN="$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-16)"

umask 077
cat > .env <<CONTEUDO
# Gerado por scripts/gerar-env.sh em $(date +%F). NUNCA commitar este arquivo.
ENV=production
DOMAIN=${DOMINIO}

POSTGRES_PASSWORD=$(aleatorio 24)
JWT_SECRET=$(aleatorio 32)
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=720

# Login da psicóloga (criado/atualizado a cada start). Para trocar a senha:
# edite ADMIN_PASSWORD e rode "docker compose up -d".
ADMIN_NAME=${ADMIN_NOME}
ADMIN_EMAIL=${ADMIN_EMAIL}
ADMIN_PASSWORD=${SENHA_ADMIN}

# Cadastro público de novas contas: desligado em produção.
ALLOW_REGISTRATION=false

# IA: configure pela tela Configurações → Inteligência Artificial (a chave
# fica criptografada no banco). Só preencha aqui se quiser uma chave padrão
# do servidor.
AI_PROVIDER=anthropic
AI_MODEL=claude-sonnet-5
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_API_KEY=

# Storage S3 (opcional — vazio = arquivos no volume app_storage da VPS)
S3_BUCKET=
S3_ENDPOINT_URL=
S3_REGION=
S3_ACCESS_KEY=
S3_SECRET_KEY=
CONTEUDO

echo
echo ".env criado (permissão 600)."
echo "Login inicial:  ${ADMIN_EMAIL}"
echo "Senha inicial:  ${SENHA_ADMIN}"
echo "Guarde essa senha num lugar seguro (ela também está no .env)."
