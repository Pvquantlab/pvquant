// font-flas.mjs — kısıtsız hatta ilk karede web fontu hazır mı: Inter Tight 500/600 (latin) dosyalarının iniş bitişi ↔ FCP.
// FCP font bitişinden önceyse ilk kare metrik eşlemeli yedek yüzle çizilmiştir (kısa yedek→web fontu değişimi görünür).
// node olc/iz/font-flas.mjs --motor chromium --hedef sonra,sonra7 --gorunum 390x844 --kosu 5
import { HEDEFLER, GORUNUMLER, motorAc, baglamAyar } from "../ortak.mjs";
const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const motor = arg("motor", "chromium"), gAd = arg("gorunum", "390x844"), kosu = Number(arg("kosu", "5")), ag = arg("ag", "yok");
const hedefler = arg("hedef", "sonra,sonra7").split(",");
const t = {}; for (const h of hedefler) t[h] = await motorAc(motor, h);
const ozet = {};
for (let k = 1; k <= kosu; k++) for (const h of hedefler) {
  const b = await t[h].newContext(baglamAyar(motor, GORUNUMLER[gAd])); const s = await b.newPage();
  // metnin İLK GÖRÜNÜR boyanması: LCP API'sindeki ilk metin adayı (font-display bloğunda görünmez metin aday olmaz)
  await s.addInitScript(() => { window.__metin = null; try { new PerformanceObserver((l) => { for (const e of l.getEntries()) if (window.__metin === null && e.element && /^(H1|P|SPAN|A)$/.test(e.element.tagName) && !e.url) window.__metin = e.startTime; }).observe({ type: "largest-contentful-paint", buffered: true }); } catch (x) { window.__metin = -1; } });
  const adres = ag === "kablo20" ? HEDEFLER[h].yok.replace(/:(\d+)$/, (_, p) => ":" + (Number(p) + 4000)) : HEDEFLER[h][ag];
  await s.goto(adres + "/", { waitUntil: "load", timeout: 120000 }); await s.waitForTimeout(1500);
  const r = await s.evaluate(() => {
    const fcp = performance.getEntriesByName("first-contentful-paint")[0]?.startTime ?? null;
    const f = performance.getEntriesByType("resource").filter((e) => /inter-tight-latin-(500|600)-normal/.test(e.name)).map((e) => e.responseEnd);
    return { fcp, fontSon: f.length ? Math.max(...f) : null, metin: window.__metin };
  });
  // LCP API'si varsa ilk görünür metin boyanması, yoksa (WebKit) FCP ile kıyas
  const ilk = r.metin !== null && r.metin >= 0 ? r.metin : r.fcp;
  const yedekle = ilk !== null && r.fontSon !== null && ilk < r.fontSon;
  (ozet[h] ??= []).push({ ...r, yedekle });
  console.log(`${motor} ${gAd} ${h.padEnd(6)} #${k} FCP ${r.fcp?.toFixed(0)} · ilk görünür metin ${r.metin === null || r.metin < 0 ? "—" : r.metin.toFixed(0)} · 500/600 font bitişi ${r.fontSon?.toFixed(0)} → ilk metin ${yedekle ? "YEDEK YÜZLE" : "web fontuyla"}`);
  await b.close();
}
const med = (a) => { a = a.filter((x) => x !== null && x >= 0).sort((x, y) => x - y); return a.length ? Math.round(a[Math.floor((a.length - 1) / 2)]) : "—"; };
for (const [h, l] of Object.entries(ozet)) console.log(`ÖZET ${motor} ${gAd} ${ag} ${h}: ilk metin yedek yüzle ${l.filter((x) => x.yedekle).length}/${l.length} · FCP medyan ${med(l.map((x) => x.fcp))} · ilk görünür metin medyan ${med(l.map((x) => x.metin))} · font bitişi medyan ${med(l.map((x) => x.fontSon))}`);
for (const x of Object.values(t)) await x.close();
