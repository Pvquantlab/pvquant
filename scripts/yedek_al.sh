#!/usr/bin/env bash
# PVQuant yedek alma (v2.67) — GUN 0 "yedek tatbikati" kalemi
# Cikti: yedekler/pvquant_<damga>.dump (pg_dump -Fc) + yedekler/artifacts_<damga>.tar.gz
set -euo pipefail
cd "$(dirname "$0")/.."
DAMGA=$(date +%Y%m%d_%H%M%S)
mkdir -p yedekler
docker compose exec -T db pg_dump -U pvquant -Fc pvquant > "yedekler/pvquant_${DAMGA}.dump"
tar czf "yedekler/artifacts_${DAMGA}.tar.gz" var/artifacts 2>/dev/null || echo "uyari: var/artifacts bos/yok"
ls -lh "yedekler/pvquant_${DAMGA}.dump" "yedekler/artifacts_${DAMGA}.tar.gz" 2>/dev/null
echo "YEDEK TAMAM: ${DAMGA}"
