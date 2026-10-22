/* v2.384 — Fontlar kendi sunucumuzdan (SIL OFL-1.1, @fontsource).
   Google Fonts @import'u kalktı: ziyaretçi IP'si üçüncü tarafa gitmez (KVKK) ve açılışı
   engelleyen @import zinciri yok. Panel aileleri: Inter (opsz 14–32 · wght 100–900; aile adı
   'Inter Variable') gövde/tablo, IBM Plex Mono 400/500/600 sayı/kod — toplu dosyalar unicode-range
   taşır; yalnız sayfadaki harflerin alt kümesi iner.
   22.10.2026 tek tasarım sistemi: başlık/etiket/düğme/KPI ailesi vitrinle ORTAK Inter Tight 400/500/600 —
   dosyaları features/vitrin/fontlar.ts yükler (Vitrin.tsx ana pakette; Türkçe alt küme dahil). Space Grotesk
   kalktı: panel iki woff2 daha az indirir, başlık kesimi vitrinin kart başlığıyla aynı olur. */
import "@fontsource-variable/inter/opsz.css";
/* 16.10 hız turu 4: tek alt küme dosyaları (latin-500.css, latin-ext-500.css …) unicode-range TAŞIMIYOR — iki yüz de
   her karakteri kapsıyor sayıldığından tarayıcı son tanımlananı (latin-ext) ASCII metin için bile önce indiriyor,
   glifi bulamayınca latin'i ARDINDAN istiyordu (ölçüldü: /yontem'de Plex Mono latin-ext → latin sırayla). Toplu
   ağırlık dosyaları aynı woff2'leri unicode-range ile tanımlar: yalnız gereken alt küme iner, çizim değişmez. */
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource/ibm-plex-mono/600.css";
