/** P-1 (24.11.2026) — gece işleri gün bloğu gruplama (TSİ gün sınırı, sayımlar, sıra) ve kart pinleri. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { gunlereGrupla, grupOzeti, gunAnahtari } from "../../src/lib/isler.ts";

const oku = (p: string) => readFileSync(new URL(`../../src/${p}`, import.meta.url), "utf8");

test("gruplama: TSİ gün sınırı, sayımlar ve sıra korunur", () => {
  const isler = [
    { is: "Program revizyonu", zaman: "2026-11-24T10:10:00+00:00", sure_sn: 0, tamam: true, durum: "ok", kod: "kgup_revizyon_kontrol" },
    { is: "Rapor gönderimi", zaman: "2026-11-24T05:10:00+00:00", sure_sn: 0, tamam: false, durum: "atlandi", kod: "rapor_gonderimi" },
    { is: "Sabah tahmini", zaman: "2026-11-24T02:00:00+00:00", sure_sn: 4, tamam: true, durum: "ok", kod: "sabah_tahmin" },
    { is: "Hava verisi", zaman: "2026-11-23T21:30:00+00:00", sure_sn: 7912, tamam: true, durum: "ok", kod: "gece_meteo" },   // 24.11 00:30 TSİ
    { is: "İletişim", zaman: "2026-11-23T19:50:00+00:00", sure_sn: 0, tamam: false, durum: "error", kod: "iletisim_kontrol" }, // 23.11 22:50 TSİ
  ];
  const g = gunlereGrupla(isler);
  assert.equal(g.length, 2);
  assert.equal(g[0].gun, "2026-11-24"); assert.equal(g[0].satirlar.length, 4);
  assert.deepEqual([g[0].tamam, g[0].atlandi, g[0].basarisiz], [3, 1, 0]);
  assert.equal(g[1].gun, "2026-11-23"); assert.deepEqual([g[1].tamam, g[1].atlandi, g[1].basarisiz], [0, 0, 1]);
  assert.equal(grupOzeti(g[0]), "3 tamam · 1 atlandı");
  assert.equal(grupOzeti(g[1]), "0 tamam · 1 başarısız");
  assert.equal(g[0].satirlar[0].kod, "kgup_revizyon_kontrol");   // sıra korunur
  assert.equal(gunAnahtari("2026-11-23T21:30:00+00:00"), "2026-11-24");
  assert.deepEqual(gunlereGrupla([]), []);
});

test("kart: gruplama + tümünü göster geçişi + atlandı etiketi kaynakta", () => {
  const d = oku("features/sayfalar/Digerleri.tsx");
  assert.match(d, /gunlereGrupla\(/);
  assert.match(d, /api\.isler\(tumu \? 300 : undefined\)/);
  assert.match(d, /slice\(0, 14\)/);                       // varsayılan görünüm eski davranış
  assert.match(d, /Tümünü göster/);
  assert.match(d, /isDurumu\(x\.tamam, x\.durum\)/);       // «atlandı (veri yazılmadı)» sözlükten
  const c = oku("api/client.ts");
  assert.match(c, /isler: async \(n\?: number\)/);
});
