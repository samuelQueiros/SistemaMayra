#!/usr/bin/env bash
# Backup do banco (Postgres) e dos arquivos enviados (fotos, PDFs, capas)
# da instalação via docker-compose.yml. Uso (na pasta do projeto):
#   ./scripts/backup.sh            # salva em ./backups/
#   BACKUP_DIR=/mnt/backups ./scripts/backup.sh
# Mantém os últimos $MANTER backups (padrão 14).
#
# Agendar todo dia às 3h (crontab -e):
#   0 3 * * * cd /opt/psicologa && ./scripts/backup.sh >> backups/backup.log 2>&1
#
# IMPORTANTE: copie os backups para FORA da VPS de tempos em tempos
# (outro servidor, Google Drive, S3...) — backup só na própria VPS some
# junto com ela.
set -euo pipefail
cd "$(dirname "$0")/.."

DESTINO="${BACKUP_DIR:-./backups}"
MANTER="${MANTER:-14}"
CARIMBO="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$DESTINO"
chmod 700 "$DESTINO"

docker compose exec -T db pg_dump -U formpsico --clean --if-exists formpsico | gzip > "$DESTINO/banco_$CARIMBO.sql.gz"
docker compose exec -T app tar -C /app/backend -czf - storage > "$DESTINO/arquivos_$CARIMBO.tar.gz"
chmod 600 "$DESTINO"/banco_"$CARIMBO".sql.gz "$DESTINO"/arquivos_"$CARIMBO".tar.gz

# Remove os mais antigos, mantendo $MANTER de cada tipo.
for prefixo in banco arquivos; do
  ls -1t "$DESTINO"/"$prefixo"_*.gz 2>/dev/null | tail -n +"$((MANTER + 1))" | xargs -r rm -f
done

echo "Backup concluído: $DESTINO/banco_$CARIMBO.sql.gz e arquivos_$CARIMBO.tar.gz"
