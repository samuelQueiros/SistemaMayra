#!/usr/bin/env bash
# Backup do banco de produção (Postgres). Uso:
#   DATABASE_URL=postgresql+psycopg://... ./backup_db.sh [destino.sql.gz]
#
# Sem destino informado, salva em backups/formpsico_AAAAMMDD_HHMMSS.sql.gz
# na própria pasta do script. Requer o `pg_dump` do cliente Postgres
# instalado na máquina que roda o backup (não precisa ser a mesma do
# servidor da aplicação).
#
# Exemplo de agendamento diário às 3h da manhã (crontab -e):
#   0 3 * * * DATABASE_URL="postgresql+psycopg://..." /caminho/backup_db.sh /backups/$(date +\%F).sql.gz

set -euo pipefail

: "${DATABASE_URL:?Defina a variável DATABASE_URL antes de rodar este script}"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESTINO="${1:-$DIR/backups/formpsico_$(date +%Y%m%d_%H%M%S).sql.gz}"

mkdir -p "$(dirname "$DESTINO")"

# pg_dump não entende o prefixo "postgresql+psycopg://" do SQLAlchemy —
# troca para "postgresql://", que é o que o pg_dump espera.
URL_PARA_PG_DUMP="${DATABASE_URL/postgresql+psycopg:\/\//postgresql://}"

pg_dump "$URL_PARA_PG_DUMP" | gzip > "$DESTINO"

echo "Backup salvo em: $DESTINO"
