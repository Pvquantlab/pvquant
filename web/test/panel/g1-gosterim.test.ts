// Faz 1 G1 (22.11.2026) — gösterim dürüstlüğü kaynak pinleri (web). Hesap değişmez; yalnız etiket, metin, rozet.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");

test("G1-a/b: Doğruluk KPI'ları günlük ortalama olduğunu ve beceri yöntemini söyler; üç WMAPE açıklaması var", () => {
  const s = oku("../../src/features/sayfalar/Dogruluk.tsx");
  assert.match(s, /günlük değerlerin ortalaması, \$\{k\.gun_sayisi\} gün/);
  assert.match(s, /Referans tahmine göre iyileşme \(pencere ortalamalarıyla\)/);
  assert.match(s, /naife_ustunluk_gun_ort_pct/, "eski günlük-oran ortalaması kendi etiketiyle görünür (sayı gizlenmez)");
  assert.match(s, /data-rol="wmape-aciklama"/);
  assert.match(s, /havuzlanmış saatlik toplam — \$\{KURAL_AD\[kural\]/, "bağımsız bölüm havuz olduğunu ve kuralı söyler");
  assert.match(s, /kapsama_pct < 90/, "ölçüm eksikliği notu");
  assert.match(s, /A: "fiziksel model \(kalibrasyonsuz\)"/);
  assert.doesNotMatch(s, /gün başı tahmini, \$\{k\.gun_sayisi\} gün ort\./, "eski belirsiz etiket kalktı");
  // E QA İ-K12-1 (23.11): deltaCip JSX olabilir; şablon dizesine gömülünce «[object Object]» basılıyordu (örnek yığında görüldü)
  assert.match(s, /: <>\{deltaCip\}; ufuk: \{k\.kova_aciklama\?\.ufuk \?\? "0–24 saat ileri"\}<\/>/, "KPI alt satırı JSX parçası olarak çizilir");
  assert.doesNotMatch(s, /\$\{deltaCip\}/, "JSX düğümü şablon dizesine gömülmez");
});

test("G1-c: vitrin yöntem metni «yeniden hesaplanmaz» demez, ölçüm kaynağını söyler, beceri pencere ortalamasıyla", () => {
  const s = oku("../../src/features/vitrin/yontem-metni.ts");
  assert.doesNotMatch(s, /yeniden hesaplanmaz/);
  assert.match(s, /yeniden hesap sayacıyla işaretlenir/);
  assert.match(s, /kamuya açık resmî üretim ölçümü/);
  assert.match(s, /pencere ortalamalarıyla/);
});

test("G1-f/g: santral türü rozeti üst şeritte, kamu_referans seçeneği, Mod A kalibrasyonsuz künyesi", () => {
  const kabuk = oku("../../src/shell/Kabuk.tsx");
  assert.match(kabuk, /ozet\.sinif\?\.rozet && \(/);
  assert.match(kabuk, /\{ozet\.sinif\.rozet\} · \{ozet\.sinif\.santral_turu_etiketi\}/);
  const santralim = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(santralim, /<option value="kamu_referans">kamu referans kaydı/);
  const tahminler = oku("../../src/features/sayfalar/Tahminler.tsx");
  assert.match(tahminler, /seri\.kalibrasyon_var === false \? " · kalibrasyonsuz fiziksel model"/);
  const client = oku("../../src/api/client.ts");
  assert.match(client, /kalibrasyon_var: g\.kalibrasyon_var \?\? null/);
  // E QA İ-K12-2 (23.11): uyarlaOzet /summary.sinif'i aktarmıyordu → rozet koşulu hiç doğru olmuyordu (örnek yığında DOM'da 0 rozet)
  assert.match(client, /sinif: g\.sinif \?\? null/, "uyarlaOzet santral sınıfını SantralOzeti'ye taşır");
  assert.match(client, /interface OzetYanit \{[\s\S]*sinif\?: \(SantralSinifi & \{ rozet\?: string \| null \}\) \| null;[\s\S]*\n\}/, "OzetYanit tipi sinif alanını tanır");
  const types = oku("../../src/api/types.ts");
  assert.match(types, /kova_aciklama\?: \{ ad: string; ufuk: string; secim: string \} \| null/);
  assert.match(types, /sinif\?: \(SantralSinifi & \{ rozet\?: string \| null \}\) \| null/);
});
