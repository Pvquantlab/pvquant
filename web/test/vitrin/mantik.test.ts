// v2.384 — vitrinin saf modülleri ve tek yöntem metni.
import { test } from "node:test";
import assert from "node:assert/strict";
import { dogrulamaDurumu } from "../../src/features/vitrin/dogrulamaDurumu.ts";
import { yuzdeTr, kisaTarihTr, ayTr } from "../../src/features/vitrin/bicim.ts";
import { numuneGun, NUMUNE_TARIH } from "../../src/features/vitrin/numuneGun.ts";
import { gunesYuksekligi, dogusBatisTrt, gokDurumu } from "../../src/features/vitrin/gunesSaati.ts";
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

test("canlı gök hesabı (R26) gündönümlerinde gök mekaniğiyle eşleşir", () => {
  // 38°K öğle yükseklikleri: 21 Haz ≈ 90−38+23,44 = 75,4° · 21 Ara ≈ 90−38−23,44 = 28,6° (±0,8 tolerans)
  const oglenMaks = (gun: string) => {
    let maks = -90;
    for (let dk = 0; dk < 240; dk += 5) {
      const t = new Date(`${gun}T08:00:00Z`);          // TRT 11:00–15:00 taraması
      t.setUTCMinutes(t.getUTCMinutes() + dk);
      maks = Math.max(maks, gunesYuksekligi(t));
    }
    return maks;
  };
  assert.ok(Math.abs(oglenMaks("2026-06-21") - 75.4) < 0.8, `yaz: ${oglenMaks("2026-06-21")}`);
  assert.ok(Math.abs(oglenMaks("2026-12-21") - 28.6) < 0.8, `kış: ${oglenMaks("2026-12-21")}`);
  const { dogus, batis } = dogusBatisTrt(new Date("2026-06-21T09:00:00Z"));
  assert.ok(dogus > 4 && dogus < 6.5 && batis > 19 && batis < 21, `yaz doğuş/batış: ${dogus}/${batis}`);
  const ogle = gokDurumu(new Date("2026-06-21T09:00:00Z"));     // TRT 12:00
  assert.equal(ogle.gunduz, true);
  assert.ok(ogle.kalanDk > 0 && ogle.kalanDk < 10 * 60);
  const gece = gokDurumu(new Date("2026-06-21T22:00:00Z"));     // TRT 01:00 (22 Haz gecesi)
  assert.equal(gece.gunduz, false);
  assert.ok(gece.kalanDk > 0 && gece.kalanDk < 8 * 60, `gece doğuşa kalan: ${gece.kalanDk}`);
});

test("gece yarısı geçişinde geri sayım sürekli (TRT 23:xx yarının doğuşunu kullanır)", () => {
  // Ekinoks gecesi: TRT 23:30 (yarin+24 dalı) ve TRT 00:00 — ikisi de pozitif, fark ≈ 30 dk.
  const oncesi = gokDurumu(new Date("2026-03-20T20:30:00Z"));   // TRT 23:30
  const sonrasi = gokDurumu(new Date("2026-03-20T21:00:00Z"));  // TRT 00:00 (21 Mar)
  assert.equal(oncesi.gunduz, false);
  assert.equal(sonrasi.gunduz, false);
  assert.ok(oncesi.kalanDk > 0 && sonrasi.kalanDk > 0);
  assert.ok(Math.abs(oncesi.kalanDk - 30 - sonrasi.kalanDk) <= 2,
    `sıçrama: 23:30'da ${oncesi.kalanDk} dk, 00:00'da ${sonrasi.kalanDk} dk`);
  const gunduzOrnek = gokDurumu(new Date("2026-03-21T09:00:00Z"));   // TRT 12:00
  assert.equal(gunduzOrnek.gunduz, true);
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

/* ── v2.413: referans kartı veri modülü — dört günlük koşu seti ── */
import {
  bulgu, gunSerisi, gunlukCF, haftaSerisi, yilSerisi,
  KOSU_GUNLERI, VARSAYILAN_GUN,
} from "../../src/features/vitrin/referansVeri.ts";

test("dört koşu günü tutarlı: p10 ≤ p90, oranlar 0..1, saatler artan (p50 kontrol üyesidir — banda kelepçeli değil, 29.09 07:00 örneği)", () => {
  assert.equal(KOSU_GUNLERI.length, 4);
  for (const g of KOSU_GUNLERI) {
    const seri = gunSerisi(g);
    assert.equal(seri.length, 15, g);
    seri.forEach((n, i) => {
      assert.ok(0 <= n.p10 && n.p10 <= n.p90 + 1e-9 && n.p90 <= 1, `${g} saat ${n.saat}`);   // 30.09 15:00 tam AC kelepçesi: p90 = 1
      assert.ok(0 <= n.p50 && n.p50 <= 1, `${g} saat ${n.saat} p50`);
      if (n.gercek !== null) assert.ok(0 <= n.gercek && n.gercek <= 1, `${g} saat ${n.saat}`);
      if (i > 0) assert.ok(n.saat > seri[i - 1].saat, `${g} saat ${n.saat}`);
    });
  }
});

test("varsayılan gün (01.10) numuneGun ile bayt-aynı — kartın bugünkü hâli korunur", () => {
  const eski = numuneGun();
  const yeni = gunSerisi(VARSAYILAN_GUN);
  assert.equal(yeni.length, eski.length);
  eski.forEach((n, i) => {
    for (const alan of ["saat", "p10", "p50", "p90", "gercek"] as const)
      assert.equal(yeni[i][alan], n[alan], `saat ${n.saat} ${alan}`);
  });
});

test("türetilmiş bulgu 01.10'da araştırma vurgusuyla birebir", () => {
  assert.equal(bulgu(VARSAYILAN_GUN)?.metin, "08:00–12:00 · gerçekleşen aralığın altında");
});

test("günlük CF ve aralık serileri: enerji anlamı korunur, veri uydurulmaz", () => {
  for (const g of KOSU_GUNLERI) {
    const { cf50, cfGercek } = gunlukCF(g);
    assert.ok(cf50 > 0.1 && cf50 < 0.5, `${g} cf50 ${cf50}`);
    assert.ok(cfGercek > 0.05 && cfGercek < 0.5, `${g} cfGercek ${cfGercek}`);
  }
  const hafta = haftaSerisi(VARSAYILAN_GUN);          // 28.09 Pzt – 04.10 Paz
  assert.equal(hafta.length, 7);
  assert.equal(hafta.filter((s) => s.cf50 !== null).length, 4);
  assert.ok(hafta.slice(4).every((s) => s.cf50 === null), "koşusu olmayan günler null kalır");
  const yil = yilSerisi(VARSAYILAN_GUN);
  assert.equal(yil.seri.length, 12);
  assert.equal(yil.seri.filter((s) => s.cf50 !== null).length, 2);  // Eyl + Eki
  assert.ok(yil.kapsam.includes("4 koşu günü"));
});
