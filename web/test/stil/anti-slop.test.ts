// Anti-slop bekçisi (kullanıcı talebi 08.10): «AI görünümü» imzalarının makine-denetlenebilir kısmı.
// İnsan-kurallı maddeler (mor-mavi gradyan, aynı gölgeli ızgara, ortalanmış hero+3 kutu,
// her yerde Inter) anti-slop.md tablosundadır; burada kaynakta EMOJİ yasağı zorlanır.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";

test("kaynakta emoji karakteri yok (dekoratif ikon/emoji yasağı)", () => {
  const kok = new URL("../../src/", import.meta.url);
  // yalnız gerçek emoji blokları: ✓/✔ gibi tipografik dingbat'ler meşrudur (onay işareti dili)
  const emoji = /[\u{1F000}-\u{1FAFF}\u{FE0F}\u{2764}\u{2B50}]/u;
  let sayi = 0;
  for (const g of readdirSync(kok, { recursive: true, withFileTypes: true })) {
    if (!g.isFile() || !/\.(tsx?|css|html)$/.test(g.name)) continue;
    sayi++;
    const icerik = readFileSync(`${g.parentPath}/${g.name}`, "utf8");
    const m = icerik.match(emoji);
    assert.equal(m, null, `${g.parentPath}/${g.name}: emoji bulundu (${m?.[0]})`);
  }
  assert.ok(sayi > 40, "kaynak dosyaları taranamadı");
});
