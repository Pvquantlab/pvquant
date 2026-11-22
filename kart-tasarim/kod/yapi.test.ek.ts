
test("TL kartları «panel kesiti»: tek yüzey, beş kart, eski vinyet ve sembol ikon yok; amber yalnız gerçekleşen çiziminde (kart-tasarim)", () => {
  const piyasa = oku("../../src/features/vitrin/TurkiyePiyasasi.tsx");
  assert.match(piyasa, /className="vt-kesit"/);
  assert.equal((piyasa.match(/^\s*\{ ad: "/gm) ?? []).length, 5);
  assert.doesNotMatch(piyasa, /vinyet-|VinyetTl|VinyetTicaret|vt-vin-kart|tek tık/i);
  const cizim = oku("../../src/features/vitrin/KartCizimleri.tsx");
  // veri renk sözleşmesi: amber (#C27803) yalnız sapma (gerçekleşen eğrisi) ve alarm (gelen ölçüm) çizimlerinde
  const amberli = [...cizim.matchAll(/export function (\w+)\(\)[\s\S]*?(?=export function|$)/g)]
    .filter((m) => m[0].includes("#C27803")).map((m) => m[1]);
  assert.deepEqual(amberli, ["CizimSapma", "CizimAlarm"]);
  assert.doesNotMatch(cizim, /#FFB4A2|#B11F47/i);   // şeftali ve eylem rengi kart çizimlerinde yok
});
