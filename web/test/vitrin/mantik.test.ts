// v2.384 — vitrinin saf modülleri ve tek yöntem metni.
import { test } from "node:test";
import assert from "node:assert/strict";
import { dogrulamaDurumu } from "../../src/features/vitrin/dogrulamaDurumu.ts";
import { yuzdeTr, kisaTarihTr, ayTr } from "../../src/features/vitrin/bicim.ts";
import { numuneGun, NUMUNE_TARIH } from "../../src/features/vitrin/numuneGun.ts";
import { ADIMLAR, METRIKLER, KISA_TANIMLAR, YONTEM_KAPANIS } from "../../src/features/vitrin/yontem-metni.ts";

test("doğrulama yanıtı dört duruma eşlenir", () => {
  assert.deepEqual(dogrulamaDurumu(null), { tur: "hata" });
  assert.deepEqual(dogrulamaDurumu(undefined), { tur: "hata" });
  assert.deepEqual(dogrulamaDurumu({ durum: "kapali" }), { tur: "kapali" });
  const acik = { durum: "acik" as const, pencere_gun: 46, wmape_pct: 5.5 };
  assert.deepEqual(dogrulamaDurumu(acik), { tur: "acik", veri: acik });
});

test("yüzde Türkçe biçimlenir; değer yoksa tire", () => {
  assert.equal(yuzdeTr(5.5), "%5,5");
  assert.equal(yuzdeTr(20), "%20");
  assert.equal(yuzdeTr(null), "—");
  assert.equal(yuzdeTr(undefined), "—");
});

test("tarih ve ay Türkçe", () => {
  assert.equal(kisaTarihTr("2026-10-01"), "1 Eki");
  assert.equal(kisaTarihTr(undefined), "—");
  assert.equal(ayTr("2026-09"), "Eylül 2026");
});

test("numune gün (01.10 koşusu) tutarlı: P10 ≤ P50 ≤ P90 < AC tavanı, saatler artan", () => {
  const gun = numuneGun();
  assert.equal(NUMUNE_TARIH, "01.10.2026");
  assert.ok(gun.length >= 10);
  gun.forEach((n, i) => {
    assert.ok(0 <= n.p10 && n.p10 <= n.p50 && n.p50 <= n.p90 && n.p90 < 1, `saat ${n.saat}`);
    assert.ok(0 <= n.gercek && n.gercek < 1, `saat ${n.saat}`);
    if (i > 0) assert.ok(n.saat > gun[i - 1].saat, `saat ${n.saat}`);
  });
  // sabah hikâyesi veriden okunur (künye ve grafik açıklaması buna dayanır): 08–11 gerçekleşen P10'un altında
  for (const s of [8, 9, 10, 11]) {
    const n = gun.find((p) => p.saat === s)!;
    assert.ok(n.gercek < n.p10, `saat ${s}: gerçekleşen aralığın altında olmalı`);
  }
});

test("yöntem metni hesapla eşleşir ve tek kaynaktan gelir", () => {
  const birlesik = (dizi: readonly (readonly [string, string])[]) => dizi.map(([, metin]) => metin).join(" ");
  for (const metin of [birlesik(METRIKLER), birlesik(KISA_TANIMLAR)]) {
    assert.match(metin, /gündüz saatlerinin oranı/);
    assert.match(metin, /kurulu gücün %2'sini/);
    assert.match(metin, /açık-gök/);
    assert.match(metin, /o günün/);
    assert.doesNotMatch(metin, /günlerin oranı/);
    assert.doesNotMatch(metin, /gök açıklığı farkı/);
  }
  assert.equal(ADIMLAR.length, 4);
  assert.equal(KISA_TANIMLAR.length, 4);
  assert.match(YONTEM_KAPANIS, /geçmiş değiştirilmez/);
  assert.match(birlesik(METRIKLER), /“Yarın = dün aynı saat”/);
  assert.match(birlesik(KISA_TANIMLAR), /“yarın = dün aynı saat”/);
});
