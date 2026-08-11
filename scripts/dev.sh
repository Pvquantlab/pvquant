#!/bin/bash
# PVQuant geliştirme ortamı — tek komut (v2.108, E.3-c kapanışı)
#   ./scripts/dev.sh          → her şeyi kaldır, sağlığı raporla
#   ./scripts/dev.sh durdur   → her şeyi kapat
# Tasarım dersleri (9 Ağu): süreçler nohup'lu (terminalle ölmez); vite --host
# ile ÇİFT AİLE dinler (localhost IPv4/IPv6 hangisine çözülürse çözülsün açılır);
# Postgres yoklaması login'in "sunucuya ulaşılamadı" tuzağını baştan yakalar.
set -u
KOK="$(cd "$(dirname "$0")/.." && pwd)"
cd "$KOK"

if [ "${1:-}" = "durdur" ]; then
  kill $(lsof -t -iTCP:5173) 2>/dev/null
  pkill -f "vite" 2>/dev/null
  echo "spa kapatıldı. (compose yığını çalışmaya devam eder; kapatmak için: docker compose stop)"
  exit 0
fi

# 1) Postgres — yoksa hiçbir şey çalışmaz, en başta söyle
if ! (echo > /dev/tcp/127.0.0.1/5432) 2>/dev/null; then
  echo "✗ Postgres (5432) KAPALI — önce veritabanını başlat (Docker/Postgres.app)."
  echo "  API ayakta görünse bile giriş 'sunucuya ulaşılamadı' verir."
  exit 1
fi
echo "✓ postgres 5432"

# 2) API — v2.114: 8000'in sahibi COMPOSE'dur (E.4 kararı). dev.sh artık
# uvicorn dikmez; yığın kapalıysa compose ile kaldırır. Kod değişince:
#   docker compose build api worker && docker compose up -d api worker  (~8 sn, v2.113)
if ! lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null; then
  echo "· compose yığını kalkıyor (api+worker)…"
  docker compose up -d api worker >/dev/null 2>&1
  sleep 5
fi
if curl -s -m 3 http://127.0.0.1:8000/v1/healthz | grep -q ok; then
  echo "✓ api 8000 (compose)"
else
  echo "✗ api KALKMADI — teşhis:"; docker compose ps api; docker compose logs --tail 5 api; exit 1
fi

# 3) SPA — çift aile (--host) + sabit port; başkası porttaysa önce temizle
if ! lsof -nP -iTCP:5173 -sTCP:LISTEN >/dev/null; then
  (cd web && nohup npm run dev -- --host --port 5173 --strictPort \
      > /tmp/pvq_web.log 2>&1 &)
  sleep 3
fi
if lsof -nP -iTCP:5173 -sTCP:LISTEN >/dev/null; then
  echo "✓ spa 5173  →  http://localhost:5173"
else
  echo "✗ spa KALKMADI — son satırlar:"; tail -8 /tmp/pvq_web.log; exit 1
fi
echo "hazır. loglar: /tmp/pvq_api.log · /tmp/pvq_web.log"
