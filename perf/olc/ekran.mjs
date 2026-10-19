// ekran.mjs — görsel regresyon referansı: motor × görünüm × sayfa tam sayfa ekran görüntüsü + giriş ekranı.
// node olc/ekran.mjs --hedef once --cikti baseline [--motor ...] [--gorunum ...]
// Belirlenimci durum: prefers-reduced-motion: reduce (video inmez, poster sahnede; kaydırma canlandırması kapalı),
// tüm sayfa bir kez aşağı kaydırılır (tembel görseller yüklensin), görseller çözülür, başa dönülür, fontlar beklenir.
import fs from "node:fs";
import path from "node:path";
import { PNG } from "pngjs";
import { KOK, HEDEFLER, GORUNUMLER, SAYFALAR, motorAc, baglamAyar } from "./ortak.mjs";

const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "once");
const cikti = path.join(KOK, arg("cikti", "baseline"), "screens");
const motorlar = arg("motor", "chromium,firefox,webkit").split(",");
const gorunumler = arg("gorunum", Object.keys(GORUNUMLER).join(",")).split(",");
fs.mkdirSync(cikti, { recursive: true });
const kayit = [];

async function hazirla(sayfa) {
  await sayfa.evaluate(async () => {
    await document.fonts.ready;
    const adim = Math.max(200, Math.floor(innerHeight * 0.8));
    for (let y = 0; y < document.documentElement.scrollHeight; y += adim) { scrollTo(0, y); await new Promise((r) => setTimeout(r, 120)); }
    scrollTo(0, document.documentElement.scrollHeight); await new Promise((r) => setTimeout(r, 300));
    await Promise.all([...document.images].map((i) => (i.complete ? (i.decode ? i.decode().catch(() => {}) : null) : new Promise((r) => { i.onload = i.onerror = r; setTimeout(r, 8000); }))));
    scrollTo(0, 0); await new Promise((r) => setTimeout(r, 600));
  });
}

/** Tam sayfa görüntü. Firefox/WebKit tek karede 32 767 aygıt pikselinden uzun görüntü alamaz (390 px «/» ≈ 37 600 px):
 *  sayfa, belge koordinatında dilimlenip (fullPage + clip) pngjs ile tek PNG'ye birleştirilir. Kısa sayfada tek çekim. */
async function tamSayfa(sayfa, dosya, dpr) {
  const { w, h } = await sayfa.evaluate(() => ({ w: document.documentElement.clientWidth, h: document.documentElement.scrollHeight }));
  const dilim = Math.floor(30000 / dpr);
  if (h <= dilim) { await sayfa.screenshot({ path: dosya, fullPage: true }); return 1; }
  const parca = [];
  for (let y = 0; y < h; y += dilim) parca.push(PNG.sync.read(await sayfa.screenshot({ fullPage: true, clip: { x: 0, y, width: w, height: Math.min(dilim, h - y) } })));
  const cikis = new PNG({ width: parca[0].width, height: parca.reduce((t, p) => t + p.height, 0) });
  let satir = 0;
  for (const p of parca) { p.data.copy(cikis.data, satir * cikis.width * 4, 0, p.width * p.height * 4); satir += p.height; }
  fs.writeFileSync(dosya, PNG.sync.write(cikis));
  return parca.length;
}

for (const motor of motorlar) {
  const tarayici = await motorAc(motor, hedef);
  for (const gAd of gorunumler) {
    const g = GORUNUMLER[gAd];
    const baglam = await tarayici.newContext(baglamAyar(motor, g, { reducedMotion: "reduce" }));
    const sayfa = await baglam.newPage();
    for (const [sAd, yol] of Object.entries(SAYFALAR)) {
      await sayfa.goto(HEDEFLER[hedef].yok + yol, { waitUntil: "load", timeout: 120000 });
      await sayfa.waitForTimeout(1500);
      await hazirla(sayfa);
      const dosya = `${motor}-${gAd}-${sAd}.png`;
      const dilim = await tamSayfa(sayfa, path.join(cikti, dosya), g.dpr);
      const boy = await sayfa.evaluate(() => ({ w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight, yatayTasma: document.documentElement.scrollWidth > innerWidth }));
      kayit.push({ motor, gorunum: gAd, sayfa: sAd, dosya, dilim, ...boy });
      // ilk ekran (hero / üst kısım) ayrıca: tasarım kıyası için
      await sayfa.screenshot({ path: path.join(cikti, `${motor}-${gAd}-${sAd}-ilk-ekran.png`) });
    }
    // giriş ekranı: «Panele giriş» (masaüstü: haptaki düğme; dar: Menü → çekmecedeki düğme)
    await sayfa.goto(HEDEFLER[hedef].yok + "/", { waitUntil: "load", timeout: 120000 });
    await sayfa.waitForTimeout(1200);
    try {
      if (g.width <= 1080) { await sayfa.locator("button.vt-menu-dugme").click(); await sayfa.locator("#vt-cekmece button", { hasText: "Panele giriş" }).click(); }
      else await sayfa.locator(".vt-ust__eylem button.vt-ust__giris").click();
      await sayfa.waitForFunction(() => !document.querySelector(".vt-ust") && document.querySelector(".giris-form input"), null, { timeout: 15000 });
      await sayfa.evaluate(() => document.fonts.ready); await sayfa.waitForTimeout(800);
      await tamSayfa(sayfa, path.join(cikti, `${motor}-${gAd}-giris.png`), g.dpr);
      kayit.push({ motor, gorunum: gAd, sayfa: "giris", dosya: `${motor}-${gAd}-giris.png` });
    } catch (e) { kayit.push({ motor, gorunum: gAd, sayfa: "giris", hata: String(e.message).split("\n")[0] }); }
    await baglam.close();
    console.log("ekran:", motor, gAd);
  }
  await tarayici.close();
}
fs.writeFileSync(path.join(cikti, "..", "ekran.json"), JSON.stringify(kayit, null, 1));
console.log("bitti", kayit.length);
