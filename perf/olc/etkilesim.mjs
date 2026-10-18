// etkilesim.mjs — INP yaklaşımı + çizim/birleştirme maliyeti (motor × görünüm, kısıtsız ağ, sıcak önbellek, «/»).
// node olc/etkilesim.mjs --hedef once --cikti baseline [--kosu 3]
// Ölçülenler (her biri 3 koşu, medyan özetleyicide):
//  - menü açma (masaüstü: «Ürün» açılırı, dar: «Menü»), CTA üzerine gelme (masaüstü), «Panele giriş» → giriş formu görünene dek
//    · girdi→sonraki kare: olay zaman damgasından ikinci rAF'a (tüm motorlar)  · Event Timing süresi (destekleyen motorda)
//  - kare süreleri: (a) hero ekrandayken 3 sn boşta (video oynuyor; filtre + cam katmanları), (b) 3 sn kaydırma (kare başı 14 px)
//    · ortanca / p95 kare aralığı, >33 ms kare oranı. NOT: başsız (headless) çizim gerçek GPU yolundan farklıdır; motorlar
//      arası ve önce/sonra KIYAS içindir, mutlak fps iddiası değildir.
import fs from "node:fs";
import path from "node:path";
import { KOK, HEDEFLER, GORUNUMLER, motorAc, baglamAyar, OLCUM_BETIGI } from "./ortak.mjs";

const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "once");
const cikti = path.join(KOK, arg("cikti", "baseline"));
const motorlar = arg("motor", "chromium,firefox,webkit").split(",");
const gorunumler = arg("gorunum", Object.keys(GORUNUMLER).join(",")).split(",");
const kosu = Number(arg("kosu", "3"));
const dosya = path.join(cikti, "etkilesim.jsonl");
const URL = HEDEFLER[hedef].yok + "/";
const yapilan = new Set(fs.existsSync(dosya) ? fs.readFileSync(dosya, "utf8").trim().split("\n").filter(Boolean).map((s) => JSON.parse(s).anahtar) : []);

const ARAC = `(() => {
  window.__girdiBekle = (tur) => new Promise((res) => {
    addEventListener(tur, (e) => { const t0 = e.timeStamp; requestAnimationFrame(() => requestAnimationFrame(() => res(performance.now() - t0))); }, { once: true, capture: true });
    setTimeout(() => res(null), 8000);
  });
  window.__kareler = (sure, kaydir) => new Promise((res) => {
    const d = []; let onceki = null; const bas = performance.now();
    const f = (t) => { if (onceki !== null) d.push(t - onceki); onceki = t; if (kaydir) window.scrollBy(0, 14);
      if (t - bas < sure) requestAnimationFrame(f); else { d.sort((a, z) => a - z); const q = (p) => d[Math.min(d.length - 1, Math.floor(p * d.length))];
        res({ kare: d.length, ortanca: q(0.5), p95: q(0.95), yavas: d.filter((x) => x > 33.4).length / Math.max(1, d.length) }); } };
    requestAnimationFrame(f);
  });
})();`;

for (const motor of motorlar) {
  const tarayici = await motorAc(motor, hedef);
  for (const gAd of gorunumler) for (let k = 1; k <= kosu; k++) {
    if (yapilan.has([hedef, motor, gAd, k].join("|"))) continue;
    const g = GORUNUMLER[gAd];
    const baglam = await tarayici.newContext(baglamAyar(motor, g));
    try {
    await baglam.addInitScript(OLCUM_BETIGI); await baglam.addInitScript(ARAC);
    const s = await baglam.newPage();
    await s.goto(URL, { waitUntil: "load", timeout: 120000 });           // önbelleği ısıt
    await s.goto(URL, { waitUntil: "load", timeout: 120000 }); await s.waitForTimeout(3500);
    const r = { anahtar: [hedef, motor, gAd, k].join("|"), hedef, motor, surum: tarayici.version(), gorunum: gAd, kosu: k };
    r.videoOynuyor = await s.evaluate(() => { const v = document.querySelector("video"); return !!v && !v.paused && v.readyState >= 2; });
    r.bosta = await s.evaluate(() => window.__kareler(3000, false));
    // menü
    const menuSecici = g.width <= 1080 ? "button.vt-menu-dugme" : "button.vt-nav__acilir >> nth=0";
    const tur = g.width <= 1080 ? "pointerdown" : "pointerdown";
    const bekle = s.evaluate((t) => window.__girdiBekle(t), tur);
    await s.locator(menuSecici).click();
    r.menuAc = await bekle;
    await s.keyboard.press("Escape"); await s.waitForTimeout(400);
    if (g.width <= 1080) { const ac = await s.evaluate(() => !document.getElementById("vt-cekmece")?.hidden); if (ac) { await s.locator("button.vt-menu-dugme").click(); await s.waitForTimeout(300); } }
    // CTA üzerine gelme (masaüstü)
    if (g.width > 1080) { const b2 = s.evaluate(() => window.__girdiBekle("pointerover")); await s.mouse.move(5, 5); await s.locator(".vt-hero__eylem a >> nth=0").hover(); r.ctaUzerine = await b2; }
    // kaydırma akıcılığı
    r.kaydirma = await s.evaluate(() => window.__kareler(3000, true));
    r.eventTiming = await s.evaluate(() => (window.__olc?.ev || []).filter((e) => e.d >= 16).map((e) => ({ ad: e.ad, d: Math.round(e.d) })).slice(0, 20));
    // giriş: «Panele giriş» → form görünür
    await s.evaluate(() => scrollTo(0, 0)); await s.waitForTimeout(300);
    try {
      if (g.width <= 1080) { await s.locator("button.vt-menu-dugme").click(); await s.waitForTimeout(250); }
      const t0 = Date.now();
      const dugme = g.width <= 1080 ? s.locator("#vt-cekmece button", { hasText: "Panele giriş" }) : s.locator(".vt-ust__eylem button.vt-ust__giris");
      const b3 = s.evaluate(() => window.__girdiBekle("pointerdown"));
      await dugme.click();
      r.girisGirdi = await b3;
      await s.waitForFunction(() => !document.querySelector(".vt-ust") && document.querySelector(".giris-form input"), null, { timeout: 15000, polling: 16 });
      r.girisSure = Date.now() - t0;
    } catch (e) { r.girisHata = String(e.message).split("\n")[0]; }
    await baglam.close();
    fs.appendFileSync(dosya, JSON.stringify(r) + "\n");
    console.log(`etkileşim ${motor} ${gAd} #${k}: menü ${r.menuAc?.toFixed?.(0)} ms · boşta p95 ${r.bosta?.p95?.toFixed?.(1)} · kaydırma p95 ${r.kaydirma?.p95?.toFixed?.(1)} yavaş %${(100 * (r.kaydirma?.yavas || 0)).toFixed(0)} · giriş ${r.girisSure ?? r.girisHata}`);
    } catch (e) {                                                   // gezinme takıldı vb.: koşu veri olarak kaydedilir, düzenek sürer
      const r = { anahtar: [hedef, motor, gAd, k].join("|"), hedef, motor, surum: tarayici.version(), gorunum: gAd, kosu: k, kosuHatasi: String(e.message).split("\n")[0] };
      fs.appendFileSync(dosya, JSON.stringify(r) + "\n"); console.log(`etkileşim ${motor} ${gAd} #${k}: KOŞU HATASI ${r.kosuHatasi}`);
      await baglam.close().catch(() => {}); continue;
    }
  }
  await tarayici.close();
}
