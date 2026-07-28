"""
PVQuant Design Tokens (Faz 2)

CLAUDE.md ve UI Tasarim Brief v2 sozlesmesinin Python karsiligi.
Tum renk, font ve boyut degerleri buradan cekilir. Bu dosya *tek* kaynak;
baska bir yerde hard-coded renk veya font olmamali.

Referans: docs/design/CLAUDE.md - Tasarim Token'lari bolumu.
"""

# =============================================================================
# RENKLER
# =============================================================================

# Marka
PRIMARY       = "#1F5288"   # Butonlar, linkler, aktif durumlar
PRIMARY_HOVER = "#173F6E"   # Birincil hover
DARK_NAVY     = "#0E1D30"   # Sol menu zemini, tooltip zemini

# Metin hiyerarsisi (uc ton)
TEXT_PRIMARY   = "#0F1B28"   # Ana metin, basliklar, tablo hucreleri
TEXT_SECONDARY = "#3D4854"   # Aciklamalar, kart alt notlari
TEXT_TERTIARY  = "#6B7684"   # Placeholder, disabled

# Yuzey
BORDER      = "#E2E6EA"      # Tum kart/giris kenarliklari
PAGE_BG     = "#F7F8F9"      # Sayfa zemini
CARD_BG     = "#FFFFFF"      # Kart zemini

# Durum renkleri
SUCCESS = "#1E9E6A"          # Kalibre rozeti, sapma 0, pozitif deltalar
WARNING = "#C9502E"          # SADECE gercek uyarilar

# Grafik veri renkleri (yalnizca grafiklerde)
CHART_ACTUAL   = "#E8940A"   # Amber - gercekleşen uretim (asla UI'da)
CHART_FORECAST = "#2D6FB5"   # Mavi kesikli - tahmin
CHART_GRID     = "#E2E6EA"   # Soluk izgara

# Mikro-etiket rengi (BUYUK HARF etiketler icin)
MICROLABEL = "#3D4854"

# =============================================================================
# TIPOGRAFI
# =============================================================================

# Font aileleri (Google Fonts uzerinden CSS'e enjekte edilir)
FONT_UI    = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"
FONT_MONO  = "'IBM Plex Mono', 'SF Mono', Menlo, Consolas, monospace"

# Boyut olcegi (px)
SIZE_MICRO   = "11.5px"     # Mikro-etiketler (BUYUK HARF)
SIZE_CAPTION = "12px"       # Kart alt notlari, damgalar
SIZE_BODY    = "14px"       # Ana govde
SIZE_LABEL   = "13px"       # Buton, giris etiketi
SIZE_H3      = "15px"       # Kart basliklari
SIZE_H2      = "18px"       # Bolum basliklari
SIZE_H1      = "22px"       # Sayfa basliklari
SIZE_HERO    = "32px"       # Hero baslik (Konya GES adi vb.)
SIZE_METRIC  = "36px"       # KPI buyuk sayilari

# Font agirlik olcegi
WEIGHT_NORMAL  = 400
WEIGHT_MEDIUM  = 500
WEIGHT_SEMI    = 600
WEIGHT_BOLD    = 700

# Mikro-etiket letter-spacing
LETTER_SPACING_MICRO = "0.08em"
LETTER_SPACING_TIGHT = "-0.02em"   # Basliklar icin

# =============================================================================
# BOSLUK (8px grid)
# =============================================================================

SPACE_XS  = "4px"    # 0.5x
SPACE_SM  = "8px"    # 1x
SPACE_MD  = "16px"   # 2x
SPACE_LG  = "24px"   # 3x
SPACE_XL  = "32px"   # 4x
SPACE_XXL = "48px"   # 6x

# =============================================================================
# KOSE YARICAPI
# =============================================================================

RADIUS_CARD    = "8px"
RADIUS_BUTTON  = "6px"
RADIUS_PILL    = "999px"    # Rozet/pill
RADIUS_PALETTE = "12px"     # Cmd+K paleti (Faz 2.5)

# =============================================================================
# LAYOUT
# =============================================================================

SIDEBAR_WIDTH   = "236px"   # Sol menu genisligi
TOPBAR_HEIGHT   = "56px"    # Ust bar yuksekligi
CONTENT_MAX     = "1280px"  # Icerik alani max genislik

# =============================================================================
# UI METINLERI (Turkce, terim sozlugu ile uyumlu)
# =============================================================================

MENU_ITEMS = [
    ("santralim",    "Santralim"),
    ("veri_yukleme", "Veri Yükleme"),
    ("kalibrasyon",  "Kalibrasyon"),
    ("tahminler",    "Tahminler"),
    ("dogruluk",     "Doğruluk"),
    ("raporlar",     "Raporlar"),
]

PRIVACY_TEXT = "Verinizin sahibi sizsiniz. Yalnızca sizin hesabınızda tutulur; dilediğiniz an dışa aktarabilir veya arşivleyebilirsiniz."  # v2.54
ORG_NAME     = "Anadolu Enerji A.S."
ORG_PLAN     = "Kurumsal plan"
ORG_INITIAL  = "A"

APP_VERSION  = "PVQuant v1.4.2"
COPYRIGHT    = "(c) 2026 PVQuant"
STATUS_TEXT  = "Sistem durumu: Normal"

USER_NAME    = "Deniz Yilmaz"
USER_ORG     = "Anadolu Enerji A.S."
USER_INITIAL = "D"
