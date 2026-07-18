#!/usr/bin/env bash
# PVQuant günlük yedek — El Kitabı P4 §4a birebir (v2.22 paketi)
set -e
cd "$(dirname "$0")/.."
mkdir -p yedekler
TARIH=$(date +%Y%m%d_%H%M)
docker compose exec -T db pg_dump -U pvquant pvquant | gzip \
  > "yedekler/pvq_${TARIH}.sql.gz"
ls -t yedekler/*.gz | tail -n +15 | xargs -r rm   # son 14 yedek kalır
echo "yedek OK: yedekler/pvq_${TARIH}.sql.gz ($(du -h yedekler/pvq_${TARIH}.sql.gz | cut -f1))"
# CRON (kullanıcı ekler):  15 1 * * *  /bin/bash <repo>/scripts/yedek.sh >> <repo>/yedekler/yedek.log 2>&1
