// load-takilma.mjs — Firefox'ta aynı sekmede aynı adrese ikinci gezinmede «load» olayı gelmiyor mu? Tekrar sayısı kadar dener;
// takılırsa bekleyen istekleri ve belge durumunu yazar. node olc/load-takilma.mjs [--hedef once] [--motor firefox] [--tekrar 15] [--gorunum 1440x900]
import { HEDEFLER, GORUNUMLER, motorAc, baglamAyar } from "./ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "once"), motor = arg("motor", "firefox"), tekrar = Number(arg("tekrar", "15")), gAd = arg("gorunum", "1440x900");
const t = await motorAc(motor, hedef);
let takilma = 0;
for (let k = 1; k <= tekrar; k++) {
  const b = await t.newContext(baglamAyar(motor, GORUNUMLER[gAd])); const s = await b.newPage();
  const bekleyen = new Map();
  s.on("request", (r) => bekleyen.set(r, Date.now()));
  s.on("requestfinished", (r) => bekleyen.delete(r)); s.on("requestfailed", (r) => bekleyen.delete(r));
  const sonuc = [];
  for (const n of [1, 2]) {
    const t0 = Date.now();
    try { await s.goto(HEDEFLER[hedef].yok + "/", { waitUntil: "load", timeout: 45000 }); sonuc.push(`${n}. ${Date.now() - t0} ms`); }
    catch (e) {
      takilma++;
      const durum = await s.evaluate(() => ({ hazir: document.readyState, img: [...document.images].filter((i) => !i.complete).map((i) => (i.currentSrc || i.src).split("/").pop()), video: document.querySelector("video")?.networkState })).catch((x) => String(x));
      sonuc.push(`${n}. TAKILDI · belge ${JSON.stringify(durum)} · bekleyen istekler: ${[...bekleyen].map(([r, z]) => `${r.resourceType()} ${r.url().split("/").pop().slice(0, 40)} (${Date.now() - z} ms)`).join(", ")}`);
    }
  }
  console.log(`#${k}`, sonuc.join(" | "));
  await b.close();
}
console.log(`takılma: ${takilma} / ${tekrar * 2} gezinme`);
await t.close();
