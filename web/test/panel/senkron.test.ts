/** 26.10 — iki panel eşzamanlama bekçisi: ortak sözlük, ortak biçimleyici, damga olay kanalı ve sayfa abonelikleri, önbellek eskitme.
 *  Kaynak pinleri: davranış değil, «aynı kavram aynı yerden» kuralı korunur. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const oku = (p: string) => readFileSync(new URL(`../../src/${p}`, import.meta.url), "utf8");

test("sözlük: iş durumu, tazelik, son veri/son tahmin ve sorun adları tek yerden", () => {
  const s = oku("lib/sozluk.ts");
  assert.match(s, /isDurumu: \{ tamam: "tamam", basarisiz: "başarısız" \}/);
  assert.match(s, /tazelik: \{ guncel: "güncel", eski: "eski" \}/);
  assert.match(s, /sonVeri: "son veri", sonTahmin: "son tahmin"/);
  assert.match(s, /kiraci_askida: "müşteri askıda"/);
  const degerler = (s.match(/"[^"]*"/g) ?? []).join(" ");   // yalnız dizge değerleri; yorumlar serbest
  assert.doesNotMatch(degerler, /kiracı|"bayat"|"taze"|düştü/);
});

test("platform Sistem ve müşteri gece işleri kartı aynı sözcükleri sözlükten alır", () => {
  const sistem = oku("features/yonetim/Sistem.tsx"), dig = oku("features/sayfalar/Digerleri.tsx"), kabuk = oku("shell/Kabuk.tsx");
  assert.match(sistem, /import \{ SOZLUK, isDurumu, tazelik, sorunAdi \} from "\.\.\/\.\.\/lib\/sozluk"/);
  assert.match(sistem, /\{isDurumu\(x\.tamam\)\}/); assert.match(sistem, /\{tazelik\(bayat\)\}/); assert.match(sistem, /\{sorunAdi\(s\)\}/);
  // eski sözcükler hiçbir dizge/şablon değerinde yok (kelime sınırıyla; kod kimlikleri .bayat/.taze ve yorumlar serbest)
  const metinler = (d: string) => (d.match(/"[^"\n]*"|`[^`]*`/g) ?? []).join(" ").replace(/\$\{[^}]*\}/g, "");   // ${…} kod ifadeleri dışarıda
  for (const [ad, d] of [["Sistem", sistem], ["sayfalar", oku("features/yonetim/sayfalar.tsx")], ["Kullanim", oku("features/yonetim/Kullanim.tsx")], ["Planlar", oku("features/yonetim/Planlar.tsx")]] as const)
    assert.doesNotMatch(metinler(d), /\b(taze|bayat|düştü)\b|Gece turu|Son koşu|Son SCADA|Piyasa fiyatı\b|kiracı/, ad);
  assert.match(sistem, /<th>Son veri<span className="birim">SCADA<\/span><\/th><th>Son tahmin<\/th>/);
  assert.match(dig, /\{isDurumu\(x\.tamam\)\}/); assert.doesNotMatch(dig, /"düştü"/);
  assert.match(kabuk, /\{SOZLUK\.sonVeri\}/); assert.match(kabuk, /\$\{SOZLUK\.sonTahmin\}/); assert.match(kabuk, /\$\{SOZLUK\.sonKontrol\}/);
});

test("zaman biçimleyici tek: yasTr/zamanTr lib/bicim'de, platform istemcisi yeniden dışa aktarır", () => {
  const bicim = oku("lib/bicim.ts"), yonetim = oku("api/yonetim.ts");
  assert.match(bicim, /export function yasTr\(/); assert.match(bicim, /export function zamanTr\(/);
  assert.match(yonetim, /export \{ yasTr, zamanTr \} from "\.\.\/lib\/bicim"/);
  assert.doesNotMatch(yonetim, /export function yasTr\(|export function zamanTr\(/);
});

test("damga değişince önbellek eskir, olay yayılır ve veri sayfaları yeniden çeker", () => {
  const ud = oku("shell/useDamga.ts"), cl = oku("api/client.ts"), olay = oku("shell/damgaOlay.ts");
  assert.match(cl, /export function bellekEskit\(\): void \{\n  for \(const \[k, v\] of bellekte\) bellekte\.set\(k, \{ veri: v\.veri, zaman: 0 \}\);/);
  assert.match(ud, /if \(!ilk\) \{ bellekEskit\(\); damgaYay\(\); setSurum/);
  assert.match(olay, /export function useDamgaSurumu\(\): number/);
  for (const [dosya, adet] of [["features/santralim/Santralim.tsx", 11], ["features/sayfalar/Tahminler.tsx", 1], ["features/sayfalar/Dogruluk.tsx", 1],
                               ["features/sayfalar/Aylik.tsx", 1], ["features/sayfalar/Digerleri.tsx", 3]] as const) {
    const s = oku(dosya);
    assert.match(s, /useDamgaSurumu/, dosya);
    const n = (s.match(/\[plantId, ds\]|\[ds\]/g) ?? []).length;
    assert.ok(n >= adet, `${dosya}: damgaya bağlı efekt ${n} < ${adet}`);
  }
});
