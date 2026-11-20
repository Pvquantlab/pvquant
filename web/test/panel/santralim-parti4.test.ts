// v2.641 — Santralim denetimi Parti 4 (web pinleri): kaynak kıyasında ölçüm sınırı seçimi + beyan edilen sınır varsayılanı,
// kirlenme modelinin sayısal terimleri UI'da, şartlı senaryo sayıları soluk.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");

test("02A-B10: kaynak kıyası sınır seçici, beyan edilen sınır varsayılan, ayrı efekt", () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(oku("../../src/api/client.ts"), /golgeSaatlik: async \(p: string, sinir\?: string\)[\s\S]{0,400}\?sinir=\$\{encodeURIComponent\(sinir\)\}/);
  assert.match(s, /const SINIR_SECENEK = \[\["inverter_ac", "inverter AC çıkışı"\], \["plant_gross_ac", "tesis brüt AC"\], \["pcc_net", "bağlantı noktası net"\], \["settlement", "uzlaştırma sayacı"\]\] as const;/);
  assert.match(s, /const beyanSinir = \(v: VeriYoluOzet \| null\): string => v\?\.beyan\?\.iec104\?\.sinir \|\| v\?\.profiller\?\.find\(\(x\) => x\.kod === v\?\.beyan\?\.baglanti\?\.profil\)\?\.sinir \|\| "inverter_ac";/);
  assert.match(s, /const refSinirEtkin = refSinir \?\? beyanSinir\(vy\); const golgeSinirEtkin = golgeSinir \?\? beyanSinir\(vy\);/);
  assert.match(s, /api\.golgeSaatlik\(plantId, golgeSinirEtkin\)[\s\S]{0,160}\}, \[plantId, santralGorunur, golgeSinirEtkin\]\);/);
  assert.doesNotMatch(s, /api\.golgeSaatlik\(plantId\)/, "sınırsız çağrı kalmadı");
  assert.match(s, /aria-label="Kaynak kıyası ölçüm sınırı" onChange=\{\(e\) => setGolgeSinir\(e\.target\.value\)\}/);
  assert.match(s, /value=\{refSinirEtkin\} aria-label="Referans ölçüm sınırı"/);
  assert.equal((s.match(/SINIR_SECENEK\.map\(/g) ?? []).length, 2, "iki seçici aynı liste");
  assert.match(s, /Son 7 günde «\{golge\.sinir_etiketi\}» sınırında canlı okumadan türetilmiş saat yok/);
  assert.match(oku("../../src/api/types.ts"), /export interface ReferansKiyasOzet \{ sinir_etiketi\?: string;/);
});

test("02B-B10: kirlenme sayısal terimleri yalnız model açıkken, Türkçe ondalık, alan terk edilince önizleme", () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /const FT_SAYISAL = \{\n  soiling_gunluk_kayip: \{ etiket: "Günlük kirlenme kaybı \(oran\)", aralik: "0–0,02"/);
  assert.match(s, /soiling_temizleme_mm: \{ etiket: "Temizleyen yağış \(mm\/gün\)", aralik: "0,5–30"/);
  assert.match(s, /soiling_baslangic: \{ etiket: "Başlangıç kirlenmesi \(oran\)", aralik: "0–0,3"/);
  assert.match(s, /\{\(ftSon\.soiling_model \?\? ft\.soiling_model\) !== "none" && \(Object\.keys\(FT_SAYISAL\) as \(keyof typeof FT_SAYISAL\)\[\]\)\.map/);
  assert.match(s, /onBlur=\{\(e\) => \{ const ham = e\.target\.value\.trim\(\); if \(ham === ""\) return; const v = sayiOkuTr\(ham\); if \(v === null\) \{ setFtMesaj\(`\$\{FT_SAYISAL\[k\]\.etiket\}: sayı olmalı \(\$\{FT_SAYISAL\[k\]\.aralik\}\)\.`\); return; \} ftDegistir\(k, String\(v\)\); \}\}/);
  assert.match(s, /String\(\(ft as unknown as Record<string, unknown>\)\[k\] \?\? ""\) === v\) delete aday\[k\]/);
});

test("02C-B13: şartlı senaryo sayıları soluk ve normal ağırlıkta", () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.equal((s.match(/className=\{kir\.kayip\.nitelik !== "tahmin" \? "soluk" : undefined\} style=\{\{ fontWeight: kir\.kayip\.nitelik !== "tahmin" \? 400 : 500 \}\}/g) ?? []).length, 2, "MWh ve TL");
  assert.match(s, /title=\{kir\.kayip\.nitelik !== "tahmin" \? "şartlı senaryo: güvenilirlik zayıf\/belirsiz; karşılaştırma için değil" : undefined\}/);
});
