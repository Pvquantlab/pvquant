// 22.10.2026 — Panel dili: görünür yüzeyde ekip iç terimi yok (anti-slop madde 7'nin panel karşılığı,
// docs/PANEL-DIL-2026-10-22.md §2 terim tablosu tek kaynak). Yorumlar ve tanımlayıcılar kapsam dışı;
// yalnız Türkçe karakter taşıyan, dolayısıyla ancak görünür metinde geçebilen biçimler taranır.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const DOSYALAR = [
  "shell/Kabuk.tsx", "App.tsx",
  "features/sayfalar/Portfoy.tsx", "features/sayfalar/Dogruluk.tsx", "features/sayfalar/Tahminler.tsx",
  "features/sayfalar/Aylik.tsx", "features/sayfalar/Digerleri.tsx", "features/sayfalar/Hakkinda.tsx",
  "features/sayfalar/JsonOnizleme.tsx", "features/santralim/Santralim.tsx", "features/giris/Giris.tsx",
];

// iç terim → müşteri dili (karşılık yalnız hata mesajı için)
const YASAK: [RegExp, string][] = [
  [/koşu/i, "tahmin / tahmin hesabı"],
  [/naif (referans|program)|naife\b/i, "referans tahmin"],   // `naif` tanımlayıcısı (API alanı) kapsam dışı
  [/\bzarf/i, "aralık"],
  [/persistans/i, "süreklilik / son ölçümlere göre düzeltme"],
  [/isabet düş/i, "tahmin doğruluğu düştü"],
  [/künye/i, "santral bilgileri"],
  [/meteoyu|meteosu/i, "hava verisi"],
  [/\bNWP\b/, "sayısal hava tahmini"],
  [/D-1\b/, "bir gün önce"],
  [/bant (kalibrasyonu|kapsaması|sınavı)/i, "aralık ayarı / aralık içinde kalan günler"],
  [/AC tavanı/i, "AC sınırı"],
  [/uzlaştırılmış/i, "santral tahminleriyle tutarlı"],
  [/API ayakta/i, "bağlantınızı kontrol edin"],
];

/** Yorumları (// … ve /* … *\/) ayıkla — kod notlarındaki tarihçe dili testin konusu değil. */
function yorumsuz(kaynak: string): string {
  return kaynak.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`])\/\/[^\n]*/g, "$1");
}

test("panel dosyalarında görünür yüzeye sızabilecek iç terim yok", () => {
  const kok = fileURLToPath(new URL("../../src/", import.meta.url));
  const ihlaller: string[] = [];
  for (const d of DOSYALAR) {
    const metin = yorumsuz(readFileSync(kok + d, "utf8"));
    for (const [desen, karsilik] of YASAK) {
      const e = desen.exec(metin);
      if (e) {
        const satir = metin.slice(0, e.index).split("\n").length;
        ihlaller.push(`${d}:${satir} «${e[0]}» → ${karsilik}`);
      }
    }
  }
  assert.deepEqual(ihlaller, [], "iç terim bulundu:\n" + ihlaller.join("\n"));
});
