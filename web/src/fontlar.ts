/* v2.384 — Fontlar kendi sunucumuzdan (SIL OFL-1.1, @fontsource).
   Google Fonts @import'u kalktı: ziyaretçi IP'si üçüncü tarafa gitmez (KVKK) ve açılışı
   engelleyen @import zinciri yok. Panel AYNI aileleri kullanır: Inter (opsz 14–32 ·
   wght 100–900; aile adı 'Inter Variable'), Space Grotesk 500/600, IBM Plex Mono
   400/500/600 — toplu dosyalar unicode-range taşır; yalnız sayfadaki harflerin alt kümesi iner. */
import "@fontsource-variable/inter/opsz.css";
/* 16.10 hız turu 4: tek alt küme dosyaları (latin-500.css, latin-ext-500.css …) unicode-range TAŞIMIYOR — iki yüz de
   her karakteri kapsıyor sayıldığından tarayıcı son tanımlananı (latin-ext) ASCII metin için bile önce indiriyor,
   glifi bulamayınca latin'i ARDINDAN istiyordu (ölçüldü: /yontem'de Plex Mono latin-ext → latin sırayla). Toplu
   ağırlık dosyaları aynı woff2'leri unicode-range ile tanımlar: yalnız gereken alt küme iner, çizim değişmez. */
import "@fontsource/space-grotesk/500.css";
import "@fontsource/space-grotesk/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource/ibm-plex-mono/600.css";
