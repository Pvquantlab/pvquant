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
LOG=$(mktemp -t pvq_kontrol); trap 'rm -f "$LOG"' EXIT   # koşu başına günlük (eşzamanlı koşular çakışmaz)
adim() { local ad="$1"; shift; if "$@" >"$LOG" 2>&1; then echo "✓ $ad"; ok=$((ok+1)); else echo "✗ $ad"; tail -25 "$LOG"; kotu=$((kotu+1)); fi; }
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
hedefler="$*"; [ -z "$hedefler" ] && hedefler=$(py_test_hedef | tr "\n" " ")   # 16.11: birden çok hedef tek satırda (satır sonu bash -c içinde ikinci komut oluyordu)
if [ -n "$hedefler" ]; then
  [ -z "$URL" ] && echo "uyarı: PVQ_TEST_DB_URL boş; DB isteyen testler atlanır"
  dburl=""; [ -n "$URL" ] && dburl="PVQ_DB_URL='$URL'"   # 16.11: boş adres geçirilmez (PVQ_DB_URL='' toplama hatası veriyordu; adres yokken varsayılan kalır)
  adim "pytest hedefli ($(echo "$hedefler" | wc -w | tr -d ' ') dosya)" bash -c "$dburl PYTHONPATH=src .venv/bin/python3 -m pytest -q -p no:cacheprovider --no-header $hedefler"
fi
if [ "$KIP" = "tam" ] || [ "$KIP" = "muhur" ]; then
  adim "web build" bash -c "cd web && npx vite build"
  adim "oxlint (taban 16 uyarı)" bash -c "cd web && n=\$(npx oxlint src 2>&1 | grep -c warning); echo \"uyarı: \$n\"; [ \"\$n\" -le 16 ]"
  if [ -n "$py_degisen" ]; then
    adim "ruff (değişen dosyalar, HEAD'e göre yeni kural kodu yok)" bash -c '
      for f in '"$(echo $py_degisen | tr "\n" " ")"'; do
        git show "HEAD:$f" > /tmp/pvq_ruff_head.py 2>/dev/null || continue
        a=$(.venv/bin/ruff check --output-format concise /tmp/pvq_ruff_head.py 2>/dev/null | sed -n "s/.*: \([A-Z]*[0-9]*\) .*/\1/p" | grep -E "^[A-Z]+[0-9]+$" | sort -u)
        b=$(.venv/bin/ruff check --output-format concise "$f" 2>/dev/null | sed -n "s/.*: \([A-Z]*[0-9]*\) .*/\1/p" | grep -E "^[A-Z]+[0-9]+$" | sort -u)   # 16.11: «Found N errors» özet satırı kural sanılmasın
        yeni=$(comm -13 <(echo "$a") <(echo "$b")); [ -n "$yeni" ] && { echo "$f yeni kural: $yeni"; exit 1; }
      done; exit 0'
  fi
fi
if [ "$KIP" = "muhur" ]; then
  # 20.11 (CI #798 dersi): kanonik HTML md5 kalkanı yalnız CI'da yaşıyordu; reporting/ değişince burada da koşar (pin ci.yml'den okunur)
  if [ -n "$(git diff --name-only HEAD -- reporting | head -1)" ]; then
    adim "rapor kalkanı (kanonik HTML md5 = ci.yml pini)" bash -c '
      cd reporting/html && rm -rf cikti && ../../.venv/bin/python3 uret.py > /dev/null 2>&1 || { echo "uret.py düştü"; exit 1; }
      bek=$(grep -o "[0-9a-f]\{32\}  cikti/PVQuant_Konya_GES_RAPOR_16sayfa.html" ../../.github/workflows/ci.yml | cut -c1-32)
      olan=$(../../.venv/bin/python3 -c "import hashlib; print(hashlib.md5(open(\"cikti/PVQuant_Konya_GES_RAPOR_16sayfa.html\", \"rb\").read()).hexdigest())")
      echo "beklenen $bek · olan $olan"; [ -n "$bek" ] && [ "$bek" = "$olan" ]'
  fi
  if [ -n "$py_degisen" ] && [ -z "$URL" ]; then
    echo "✗ PVQ_TEST_DB_URL boş: mühür kipinde tam pytest test DB ister (RLS/yetki testleri DB'siz anlamsız)"; kotu=$((kotu+1))
  elif [ -n "$py_degisen" ]; then
    adim "tam pytest (sahip rolü, test DB)" bash -c "PVQ_DB_URL='$URL' PYTHONPATH=src .venv/bin/python3 -m pytest -q -p no:cacheprovider --no-header"
    adim "CI taklidi (TZ=UTC, pvq_api)" bash -c "TZ=UTC PVQ_BAKIM_DB_URL='$URL' PVQ_DB_URL='postgresql+psycopg://pvq_api:pvq_api_ci@localhost:55432/pvquant' PYTHONPATH=src .venv/bin/python3 -m pytest -q -p no:cacheprovider --no-header"
  else
    echo "· Python değişmedi: tam pytest atlandı (CI yine koşar)"
  fi
fi
echo "— $ok geçti, $kotu düştü ($KIP)"; [ "$kotu" = "0" ]
