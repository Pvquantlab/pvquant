// cerez-sina.mjs — çalışma zamanı çerez/depolama envanteri: dört motorda «/» ve «/yontem» açılıp 8 sn beklenir; çerezler,
// localStorage/sessionStorage anahtarları ve istenen kökenler listelenir. node olc/cerez-sina.mjs --hedef fable5-once
import { HEDEFLER, GORUNUMLER, SAYFALAR, motorAc, baglamAyar } from "./ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "fable5-once");
for (const motor of arg("motor", "chromium,firefox,webkit,edge").split(",")) {
  const t = await motorAc(motor, hedef);
  for (const [sAd, yol] of Object.entries(SAYFALAR)) {
    const c = await t.newContext(baglamAyar(motor, GORUNUMLER["390x844"])); const p = await c.newPage();
    const kokenler = new Set();
    p.on("request", (r) => kokenler.add(new URL(r.url()).origin));
    await p.goto(HEDEFLER[hedef].yok + yol, { waitUntil: "load" }); await p.waitForTimeout(8000);
    await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); await p.waitForTimeout(2000);
    const cerez = await c.cookies();
    const depo = await p.evaluate(() => ({ local: Object.keys(localStorage), session: Object.keys(sessionStorage) }));
    console.log(`${motor} ${sAd}: çerez ${cerez.length} ${JSON.stringify(cerez.map((k) => k.name))} · localStorage ${JSON.stringify(depo.local)} · sessionStorage ${JSON.stringify(depo.session)} · kökenler ${[...kokenler].join(" ")}`);
    await c.close();
  }
  await t.close();
}
