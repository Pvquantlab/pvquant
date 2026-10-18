#!/bin/bash
# derle.sh <ad> <git-ref> — üretimdeki Dockerfile.web adımlarının aynısı: web/ ağacı ref'ten dışa aktarılır,
# npm ci, VITE_API_URL=. ile derleme, onsikistir (br/gz eşleri). Çıktı: perf/.replika/<ad>/dist
set -euo pipefail
AD=$1; REF=$2
KOK=$(git rev-parse --show-toplevel); HEDEF="$KOK/perf/.replika/$AD"
rm -rf "$HEDEF"; mkdir -p "$HEDEF/src"
git -C "$KOK" archive "$REF" web | tar -x -C "$HEDEF/src"
cd "$HEDEF/src/web"
npm ci --no-audit --no-fund > "$HEDEF/npm-ci.log" 2>&1
VITE_API_URL=. npm run build > "$HEDEF/build.log" 2>&1
node scripts/onsikistir.mjs dist >> "$HEDEF/build.log" 2>&1
mv dist "$HEDEF/dist"
git -C "$KOK" rev-parse "$REF" > "$HEDEF/REF"
echo "derlendi: $AD ($(cat "$HEDEF/REF" | cut -c1-7)) → $HEDEF/dist ($(du -sh "$HEDEF/dist" | cut -f1))"
