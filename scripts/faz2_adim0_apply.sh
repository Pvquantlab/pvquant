#!/usr/bin/env bash
# =============================================================================
# PVQuant Faz 2 - Adim 0 Apply Script (v2)
# =============================================================================
# Kaynak: ~/Desktop/PVQuant_UI_Tasarim/
# Belge adlari kaynakta bosluklu HTML dahil dogru esleniyor.
# =============================================================================

set -euo pipefail

# --- Ayarlar ---
REPO_DIR="$HOME/Desktop/pvquant"
SOURCE_DIR="$HOME/Desktop/PVQuant_UI_Tasarim"
EXPECTED_BRANCH="faz1.9-tilt-fit"
NEW_BRANCH="faz2-ui"

DOC_HTML_SRC="PVQuant Prototip Final.html"
DOC_HTML_DST="PVQuant_Prototip_Final.html"
DOC_BRIEF_SRC="PVQuant_UI_Tasarim_Brief_v2.md"
DOC_BRIEF_DST="PVQuant_UI_Tasarim_Brief_v2.md"
DOC_CLAUDE_SRC="CLAUDE.md"
DOC_CLAUDE_DST="CLAUDE.md"

# --- Renkler ---
if [ -t 1 ]; then
  R=$'\033[0;31m'; G=$'\033[0;32m'; Y=$'\033[0;33m'; B=$'\033[0;34m'; N=$'\033[0m'
else
  R=''; G=''; Y=''; B=''; N=''
fi

say()  { echo "${B}==>${N} $*"; }
ok()   { echo "${G}  OK${N} $*"; }
warn() { echo "${Y}  !!${N} $*"; }
die()  { echo "${R}  XX HATA:${N} $*" >&2; exit 1; }

# --- 0. Kontroller ---
say "Kontroller"

[ -d "$REPO_DIR" ] || die "Repo bulunamadi: $REPO_DIR"
cd "$REPO_DIR"
ok "Dizin: $REPO_DIR"

current_branch=$(git rev-parse --abbrev-ref HEAD)
[ "$current_branch" = "$EXPECTED_BRANCH" ] \
  || die "Beklenen dal: $EXPECTED_BRANCH, mevcut: $current_branch"
ok "Dal dogru: $current_branch"

if ! git diff-index --quiet HEAD --; then
  die "Working tree kirli. Once commit veya stash yap."
fi
ok "Working tree temiz"

for f in "$DOC_HTML_SRC" "$DOC_BRIEF_SRC" "$DOC_CLAUDE_SRC"; do
  [ -f "$SOURCE_DIR/$f" ] || die "Belge bulunamadi: $SOURCE_DIR/$f"
done
ok "3 tasarim belgesi kaynak dizinde"

if git show-ref --verify --quiet "refs/heads/$NEW_BRANCH"; then
  die "$NEW_BRANCH dali zaten var. Silmek icin: git branch -D $NEW_BRANCH"
fi
ok "$NEW_BRANCH dali yok - olusturulabilir"

# --- 1. Yeni dal ---
say "1. Yeni dal olusturuluyor: $NEW_BRANCH"
git checkout -b "$NEW_BRANCH"
ok "Dal aktif: $(git rev-parse --abbrev-ref HEAD)"

# --- 2. config.toml ---
say "2. .streamlit/config.toml anayasa uyumlu hale getiriliyor"

if [ -f ".streamlit/config.toml" ]; then
  cp ".streamlit/config.toml" ".streamlit/config.toml.faz1_backup"
  ok "Eski config yedeklendi"
else
  mkdir -p .streamlit
fi

cat > .streamlit/config.toml << 'CONFIG_EOF'
# PVQuant Streamlit theme
# CLAUDE.md ve UI Tasarim Brief v2 ile uyumlu.
# Detayli tipografi ve renk sistemi global CSS ile enjekte edilir (Adim 1).

[theme]
base = "light"
primaryColor = "#1F5288"
backgroundColor = "#F7F8F9"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#0F1B28"
font = "sans serif"

[server]
runOnSave = true
CONFIG_EOF
ok "Yeni config.toml yazildi"

# --- 3. Eski frontend sil ---
say "3. Eski frontend dosyalari siliniyor"

for f in "frontend/app.py" "frontend/app.py.faz1_backup"; do
  if [ -f "$f" ]; then
    git rm -f "$f" > /dev/null
    ok "Silindi: $f"
  else
    warn "Yoktu: $f"
  fi
done

# --- 4. docs/design/ ---
say "4. docs/design/ olusturuluyor"
mkdir -p docs/design

cp "$SOURCE_DIR/$DOC_HTML_SRC"   "docs/design/$DOC_HTML_DST"
ok "Kopyalandi: $DOC_HTML_DST"

cp "$SOURCE_DIR/$DOC_BRIEF_SRC"  "docs/design/$DOC_BRIEF_DST"
ok "Kopyalandi: $DOC_BRIEF_DST"

cp "$SOURCE_DIR/$DOC_CLAUDE_SRC" "docs/design/$DOC_CLAUDE_DST"
ok "Kopyalandi: $DOC_CLAUDE_DST"

# --- 5. README.md ---
say "5. frontend/README.md guncelleniyor"

if [ -f "frontend/README.md" ]; then
  cp "frontend/README.md" "frontend/README.md.faz1_backup"
  ok "Eski README yedeklendi"
fi

cat > frontend/README.md << 'README_EOF'
# PVQuant Frontend - Streamlit UI (Faz 2)

Bu klasor, PVQuant kullanici arayuzunun Streamlit tabanli implementasyonunu icerir.
Backend'e (src/pvquant/) yalnizca cagirarak bagli calisir; backend degistirilmez.

## Kaynak belgeler

- docs/design/CLAUDE.md - Faz 2 kod tarafi sozlesmesi
- docs/design/PVQuant_UI_Tasarim_Brief_v2.md - Gorsel/UX anayasasi
- docs/design/PVQuant_Prototip_Final.html - Onaylanmis gorsel prototip

## Calistirmak

    cd ~/Desktop/pvquant
    source .venv/bin/activate
    streamlit run frontend/Ana.py

Ana.py Faz 2 Adim 1'de olusacak.

## Cagrilacak backend fonksiyonlari

CLAUDE.md sozlesmesine gore UI yalnizca su 4 arayuzu cagirir:

- calibrate_from_scada
- forecast_7day
- OpenMeteoClient
- load_csv

## Gizlilik denetimi

Her PR/commit oncesi UI metinlerinde yasak kelime taramasi yapilir.
Detay: docs/design/CLAUDE.md - Gizlilik Anayasasi bolumu.
README_EOF
ok "Yeni README yazildi"

# --- 6. Gizlilik grep'i ---
say "6. Gizlilik grep'i (baseline)"

FORBIDDEN=("Erbs" "Perez" "Faiman" "Barhdadi" "ModelSelector" "eta_bos" "Open-Meteo")

hits_total=0
for term in "${FORBIDDEN[@]}"; do
  count=$(grep -riIF "$term" frontend/ docs/design/ 2>/dev/null | wc -l | tr -d ' ')
  if [ "$count" -gt 0 ]; then
    hits_total=$((hits_total + count))
    warn "'$term': $count esleşme"
  fi
done

if [ "$hits_total" -eq 0 ]; then
  ok "Yasak kelime yok"
else
  echo ""
  warn "Toplam $hits_total esleşme - hepsi docs/design/ icinde referans belgede ise sorun yok"
fi

# --- 7. Ozet ---
echo ""
say "Ozet"
git status --short
echo ""

say "Sonraki adimlar"
echo ""
echo "  1. Kontrol:"
echo "       git status"
echo "       ls docs/design/"
echo ""
echo "  2. Testler yesil mi:"
echo "       pytest tests/ --tb=no -q"
echo ""
echo "  3. Commit:"
echo "       git add docs/design/ frontend/README.md .streamlit/config.toml"
echo "       git commit -m 'chore: Faz 2 UI zemin - tasarim belgeleri + temizlik + config anayasa uyumu'"
echo ""

ok "Adim 0 apply script tamam."
