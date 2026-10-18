// bolum-boy.mjs — motorlar arası satır kırılımı farkı: «/» bölümlerinin ve metin bloklarının yükseklikleri (Chromium ↔ Firefox ↔ WebKit).
// node olc/bolum-boy.mjs [--hedef once] [--gorunum 390x844,1440x900]
import { HEDEFLER, GORUNUMLER, motorAc, baglamAyar } from "./ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "once");
const sonuc = {};
for (const motor of ["chromium", "firefox", "webkit"]) {
  const t = await motorAc(motor, hedef);
  for (const gAd of arg("gorunum", "390x844,1440x900").split(",")) {
    const b = await t.newContext(baglamAyar(motor, GORUNUMLER[gAd], { reducedMotion: "reduce" })); const s = await b.newPage();
    await s.goto(HEDEFLER[hedef].yok + "/", { waitUntil: "load" }); await s.waitForTimeout(1500);
    sonuc[motor + "|" + gAd] = await s.evaluate(async () => { await document.fonts.ready;
      const r = {}; document.querySelectorAll("main > section, main > div, footer").forEach((e, i) => { r[`${i}:${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""}.${(e.className || "").toString().split(" ")[0]}`] = Math.round(e.getBoundingClientRect().height); });
      const metin = {}; document.querySelectorAll("h1, h2, h3, p").forEach((e, i) => { const lh = parseFloat(getComputedStyle(e).lineHeight) || 1; metin[i + ":" + e.tagName + ":" + e.textContent.trim().slice(0, 30)] = Math.round(e.getBoundingClientRect().height / lh); });
      return { bolum: r, satir: metin, toplam: document.documentElement.scrollHeight }; });
    await b.close();
  }
  await t.close();
}
for (const gAd of arg("gorunum", "390x844,1440x900").split(",")) {
  const [c, f, w] = ["chromium", "firefox", "webkit"].map((m) => sonuc[m + "|" + gAd]);
  console.log(`\n== ${gAd} toplam: ch ${c.toplam} · ff ${f.toplam} · wk ${w.toplam}`);
  for (const k of Object.keys(c.bolum)) if (c.bolum[k] !== f.bolum[k] || c.bolum[k] !== w.bolum[k]) console.log(`  bölüm ${k}: ch ${c.bolum[k]} ff ${f.bolum[k]} wk ${w.bolum[k]}`);
  for (const k of Object.keys(c.satir)) if (c.satir[k] !== f.satir[k] || c.satir[k] !== w.satir[k]) console.log(`  satır ${k}: ch ${c.satir[k]} ff ${f.satir[k]} wk ${w.satir[k]}`);
}
