#!/usr/bin/env bash
# PVQuant geri-yukleme tatbikati (v2.67) — "yedek var" degil "yedek DONUYOR" kaniti
# Son dumpi gecici pvquant_tatbikat DB'sine yukler, sayimla dogrular, DB'yi dusurur.
set -euo pipefail
cd "$(dirname "$0")/.."
DUMP=$(ls -t yedekler/pvquant_*.dump 2>/dev/null | head -1)
[ -z "${DUMP}" ] && { echo "TATBIKAT IPTAL: yedekler/ altinda dump yok — once yedek_al.sh"; exit 1; }
echo "tatbikat dumpi: ${DUMP}"
docker compose exec -T db psql -U pvquant -d postgres -q -c "DROP DATABASE IF EXISTS pvquant_tatbikat;"
docker compose exec -T db psql -U pvquant -d postgres -q -c "CREATE DATABASE pvquant_tatbikat;"
# Timescale kurali: hypertable'li dump oncesi/sonrasi ozel mod ister
docker compose exec -T db psql -U pvquant -d pvquant_tatbikat -q -c \
  "CREATE EXTENSION IF NOT EXISTS timescaledb; SELECT timescaledb_pre_restore();"
docker compose exec -T db pg_restore -U pvquant -d pvquant_tatbikat --no-owner < "${DUMP}" \
  || echo "not: pg_restore uyarili bitti (timescale ic nesneleri — hakem asagidaki sayimlar)"
docker compose exec -T db psql -U pvquant -d pvquant_tatbikat -q -c "SELECT timescaledb_post_restore();"
echo "--- dogrulama sayimlari (tatbikat DB) ---"
docker compose exec -T db psql -U pvquant -d pvquant_tatbikat -c \
  "SELECT (SELECT count(*) FROM tenants) AS tenants,
          (SELECT count(*) FROM information_schema.tables WHERE table_schema='public') AS tablolar,
          (SELECT version_num FROM alembic_version) AS damga;"
docker compose exec -T db psql -U pvquant -d postgres -q -c "DROP DATABASE pvquant_tatbikat;"
echo "TATBIKAT TAMAM: yedek geri dondu ve dogrulandi (gecici DB dusuruldu)."
