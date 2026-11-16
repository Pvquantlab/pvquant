#!/usr/bin/env bash
# PVQuant — kademeli kontrol (16.11.2026 çalışma akışı standardı; bkz. docs/CALISMA-AKISI.md)
#   hizli  : düzenleme sırasında, saniyeler (tsc + web testleri + değişen Python dosyalarının testleri)
#   tam    : parti kapanırken (hizli + prod build + oxlint + Python hedefli dosyalar + ruff HEAD kıyası)
#   muhur  : commit öncesi tek sefer (tam + tam pytest test DB'de + CI taklidi TZ=UTC/pvq_api)
# Kullanım: scripts/kontrol.sh hizli|tam|muhur [pytest dosyaları...]
set -u
KOK="$(cd "$(dirname "$0")/.." && pwd)"; cd "$KOK" || exit 1
KIP="${1:-hizli}"; shift || true
URL="${PVQ_TEST_DB_URL:-}"
ok=0; kotu=0
adim() { local ad="$1"; shift; if "$@" >/tmp/pvq_kontrol_adim.log 2>&1; then echo "✓ $ad"; ok=$((ok+1)); else echo "✗ $ad"; tail -25 /tmp/pvq_kontrol_adim.log; kotu=$((kotu+1)); fi; }
web_degisti=$(git diff --name-only HEAD -- web | wc -l | tr -d ' ')
py_degisen=$(git diff --name-only HEAD -- src apps tests | grep '\.py$' || true)
py_test_hedef() {   # değişen kaynak dosyasının testlerini kaba eşleşmeyle bul: src/.../x_service.py → tests/test_x*.py
  local f; for f in $py_degisen; do case "$f" in tests/*) echo "$f";; *) local b; b=$(basename "$f" .py | sed 's/_service$//'); ls tests/test_"$b"*.py 2>/dev/null;; esac; done | sort -u
}
echo "kip: $KIP · web değişen: $web_degisti dosya · python değişen: $(echo "$py_degisen" | grep -c . || true) dosya"
if [ "$web_degisti" != "0" ] || [ "$KIP" != "hizli" ]; then
  adim "web tsc" bash -c "cd web && npx tsc -b"
  adim "web testleri" bash -c "cd web && npm test --silent"
fi
hedefler="$*"; [ -z "$hedefler" ] && hedefler=$(py_test_hedef)
if [ -n "$hedefler" ]; then
  [ -z "$URL" ] && echo "uyarı: PVQ_TEST_DB_URL boş; DB isteyen testler atlanır"
  adim "pytest hedefli ($(echo "$hedefler" | wc -w | tr -d ' ') dosya)" bash -c "PVQ_DB_URL='$URL' PYTHONPATH=src .venv/bin/python3 -m pytest -q -p no:cacheprovider --no-header $hedefler"
fi
if [ "$KIP" = "tam" ] || [ "$KIP" = "muhur" ]; then
  adim "web build" bash -c "cd web && npx vite build"
  adim "oxlint (taban 16 uyarı)" bash -c "cd web && n=\$(npx oxlint src 2>&1 | grep -c warning); echo \"uyarı: \$n\"; [ \"\$n\" -le 16 ]"
  if [ -n "$py_degisen" ]; then
    adim "ruff (değişen dosyalar, HEAD'e göre yeni kural kodu yok)" bash -c '
      for f in '"$(echo $py_degisen | tr "\n" " ")"'; do
        git show "HEAD:$f" > /tmp/pvq_ruff_head.py 2>/dev/null || continue
        a=$(.venv/bin/ruff check --output-format concise /tmp/pvq_ruff_head.py 2>/dev/null | sed "s/.*: \([A-Z]*[0-9]*\) .*/\1/" | sort -u)
        b=$(.venv/bin/ruff check --output-format concise "$f" 2>/dev/null | sed "s/.*: \([A-Z]*[0-9]*\) .*/\1/" | sort -u)
        yeni=$(comm -13 <(echo "$a") <(echo "$b")); [ -n "$yeni" ] && { echo "$f yeni kural: $yeni"; exit 1; }
      done; exit 0'
  fi
fi
if [ "$KIP" = "muhur" ]; then
  if [ -n "$py_degisen" ]; then
    adim "tam pytest (sahip rolü, test DB)" bash -c "PVQ_DB_URL='$URL' PYTHONPATH=src .venv/bin/python3 -m pytest -q -p no:cacheprovider --no-header"
    adim "CI taklidi (TZ=UTC, pvq_api)" bash -c "TZ=UTC PVQ_BAKIM_DB_URL='$URL' PVQ_DB_URL='postgresql+psycopg://pvq_api:pvq_api_ci@localhost:55432/pvquant' PYTHONPATH=src .venv/bin/python3 -m pytest -q -p no:cacheprovider --no-header"
  else
    echo "· Python değişmedi: tam pytest atlandı (CI yine koşar)"
  fi
fi
echo "— $ok geçti, $kotu düştü ($KIP)"; [ "$kotu" = "0" ]
