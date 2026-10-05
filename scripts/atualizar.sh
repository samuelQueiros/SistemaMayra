#!/usr/bin/env bash
# Atualiza o sistema na VPS: backup → código novo → rebuild → sobe.
# Uso (na pasta do projeto): ./scripts/atualizar.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "1/4 Backup antes de atualizar…"
./scripts/backup.sh

echo "2/4 Baixando o código novo…"
git pull --ff-only

echo "3/4 Reconstruindo e subindo (as migrations rodam sozinhas no start)…"
docker compose up -d --build

echo "4/4 Conferindo a saúde do app…"
for _ in $(seq 1 30); do
  if docker compose exec -T app python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" 2>/dev/null; then
    echo "Pronto: sistema atualizado e respondendo."
    exit 0
  fi
  sleep 3
done
echo "O app não respondeu. Veja os logs: docker compose logs --tail=100 app" >&2
exit 1
