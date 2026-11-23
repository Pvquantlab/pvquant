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
  const types = oku("../../src/api/types.ts");
  assert.match(types, /kova_aciklama\?: \{ ad: string; ufuk: string; secim: string \} \| null/);
  assert.match(types, /sinif\?: \(SantralSinifi & \{ rozet\?: string \| null \}\) \| null/);
});
