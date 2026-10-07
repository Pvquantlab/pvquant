// v2.415 Hat B1 — panel durum dili bekçisi: yükleme/boş/hata TEK kalıptan (lib/Durum.tsx).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";

const kok = new URL("../../src/features/", import.meta.url);
const dosyalar: string[] = [];
for (const g of readdirSync(kok, { recursive: true, withFileTypes: true }))
  if (g.isFile() && /\.tsx?$/.test(g.name) && !g.parentPath.includes("vitrin"))
    dosyalar.push(`${g.parentPath}/${g.name}`);

test("ad-hoc «Yükleniyor» div'i yasak — Durum.tsx kalıbı kullanılır (bilesen-dili durum matrisi)", () => {
  assert.ok(dosyalar.length > 10, "panel dosyaları bulunamadı");
  for (const d of dosyalar) {
    const icerik = readFileSync(d, "utf8");
    // blok kalıpları yasak (sayfa/kart yüklemesi Durum kalıbından gelir);
    // düğme İÇİ «Yükleniyor…» metin takası serbesttir (buton-loading kalıbı, durum matrisi)
    assert.doesNotMatch(icerik, /style=\{\{[^}]*\}\}\s*>\s*Yükleniyor/u, d);
    assert.doesNotMatch(icerik, /className="soluk"[^>]*>\s*Yükleniyor/u, d);
  }
});

test("Durum bileşenleri sözleşmesi: iskelet nötr, hata gerçek eylem taşır", () => {
  const durum = readFileSync(new URL("../../src/lib/Durum.tsx", import.meta.url), "utf8");
  assert.match(durum, /role="status"/);
  assert.match(durum, /role="alert"/);
  assert.match(durum, /Yeniden dene/);
  assert.doesNotMatch(durum, /path d=|<svg[^>]*viewBox="0 0 \d+ \d+"[^>]*>\s*<path/, "iskelette sahte eğri yok");
});
