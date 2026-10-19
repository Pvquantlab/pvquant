// filtre-esdeger.mjs — «ayrışık» keskinleştirme filtresinin özgün feConvolveMatrix ile piksel eşdeğerliği.
// node olc/filtre-esdeger.mjs [--surucu firefox-stok,pw-firefox,pw-chromium,pw-webkit] [--gorunum 1440x900,390x844] [--basli]
// Durağan hedef: «videosuz» kenar (mp4 → 404) — video hiç oynamaz, poster <img> (aynı filtreli) sahnede kalır.
// Her durumda hero bölgesinin ekran görüntüsü alınır; özgün filtreye göre kanal başına en büyük fark ve fark dağılımı.
// Durumlar: ozgun (sayfa olduğu gibi) · ozgun-tekrar (gürültü tabanı) · ayrisik-d1/dpr (1 aygıt pikseli) · ayrisik-d1 (1 CSS pikseli) · filtresiz
import fs from "node:fs";
import path from "node:path";
import { PNG } from "pngjs";
import { chromium, firefox, webkit } from "playwright";
import puppeteer from "puppeteer-core";
import { KOK, GORUNUMLER, HEDEFLER } from "./ortak.mjs";

const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const basli = process.argv.includes("--basli");
const suruculer = arg("surucu", "firefox-stok,pw-firefox").split(",");
const gorunumler = arg("gorunum", "1440x900,390x844").split(",");
const cikti = path.join(KOK, arg("cikti", "analiz/filtre"));
fs.mkdirSync(cikti, { recursive: true });
// --kip poster: videosuz kenar (mp4 → 404), poster <img> sahnede · --kip video: video 10,0 sn karesinde duraklatılır, poster gizlenir
const kip = arg("kip", "poster");
const URL0 = kip === "video" ? "https://localhost:18443/" : "https://localhost:18445/";
const spki = fs.readFileSync(path.join(KOK, HEDEFLER.once.spki), "utf8").trim();
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
const AYRISIK = (d) => `<filter id="vt-keskin-ab" color-interpolation-filters="sRGB" x="0" y="0" width="1" height="1">
  <feOffset in="SourceGraphic" dx="${d}" dy="0" result="l"/><feOffset in="SourceGraphic" dx="-${d}" dy="0" result="r"/>
  <feOffset in="SourceGraphic" dx="0" dy="${d}" result="u"/><feOffset in="SourceGraphic" dx="0" dy="-${d}" result="a"/>
  <feComposite in="l" in2="r" operator="arithmetic" k2=".5" k3=".5" result="lr"/><feComposite in="u" in2="a" operator="arithmetic" k2=".5" k3=".5" result="ua"/>
  <feComposite in="lr" in2="ua" operator="arithmetic" k2=".5" k3=".5" result="m"/>
  <feComposite in="SourceGraphic" in2="m" operator="arithmetic" k2="2.8" k3="-1.8"/></filter>`;

async function ac(surucu, g) {
  if (surucu === "firefox-stok") {
    const t = await puppeteer.launch({ browser: "firefox", executablePath: "/Applications/Firefox.app/Contents/MacOS/firefox", headless: !basli, acceptInsecureCerts: true, defaultViewport: null });
    const s = await t.newPage(); await s.setViewport({ width: g.width, height: g.height, deviceScaleFactor: g.dpr });
    return { surum: await t.version(), git: (u) => s.goto(u, { waitUntil: "load" }), deger: (f, a) => s.evaluate(f, a), resim: (clip) => s.screenshot({ clip, type: "png" }), kapat: () => t.close() };
  }
  const motor = { "pw-chromium": chromium, "pw-firefox": firefox, "pw-webkit": webkit }[surucu];
  const t = await motor.launch({ headless: !basli, args: motor === chromium ? ["--ignore-certificate-errors-spki-list=" + spki] : [] });
  const b = await t.newContext({ viewport: { width: g.width, height: g.height }, deviceScaleFactor: g.dpr, ignoreHTTPSErrors: true });
  const s = await b.newPage();
  return { surum: t.version(), git: (u) => s.goto(u, { waitUntil: "load" }), deger: (f, a) => s.evaluate(f, a), resim: (clip) => s.screenshot({ clip, type: "png" }), kapat: () => t.close() };
}

const sonuc = [];
for (const surucu of suruculer) for (const gAd of gorunumler) {
  const g = GORUNUMLER[gAd];
  const t = await ac(surucu, g);
  await t.git(URL0); await bekle(2500);
  if (kip === "video") {
    const durum = await t.deger(async () => { const v = document.querySelector("video.vt-hero__video"); const b = performance.now();
      while (performance.now() - b < 30000 && !(v && !v.paused && v.readyState >= 3)) await new Promise((r) => setTimeout(r, 100));
      v.pause(); v.currentTime = 10.0; await new Promise((r) => { v.addEventListener("seeked", r, { once: true }); setTimeout(r, 5000); });
      document.querySelector("img.vt-hero__poster")?.style.setProperty("visibility", "hidden", "important");
      return { oynadi: v.readyState, t: v.currentTime, kaynak: v.currentSrc.split("/").pop() }; });
    console.log("video karesi:", JSON.stringify(durum)); await bekle(1500);
  }
  const kutu = await t.deger(() => { const p = document.querySelector("img.vt-hero__poster"); const r = p.getBoundingClientRect();
    return { x: Math.max(0, r.left), y: Math.max(0, r.top), width: Math.min(innerWidth, r.width), height: Math.min(innerHeight, r.height), tamam: p.complete, gecti: p.classList.contains("is-gecti"), filtre: getComputedStyle(p).filter }; });
  // hero üstündeki yüzeyleri gizle (metin, cam, örtü): yalnız poster pikselleri kıyaslanır
  await t.deger(() => { const e = document.createElement("style"); e.id = "__gizle"; e.textContent = ".vt-ust, .vt-hero .vt-kap, .vt-hero__ortu, .vt-hero::after, .vt-hero::before, .vt-bolumcubuk { visibility: hidden !important; } .vt-hero::after, .vt-hero::before { display: none !important; }"; document.head.appendChild(e); });
  await bekle(800);
  const durumlar = [["ozgun", null], ["ozgun-tekrar", null], ["ayrisik-d1/dpr", (1.001 / g.dpr).toFixed(4)], ["ayrisik-d1", "1"], ["filtresiz", "yok"]];
  const resim = {};
  for (const [ad, d] of durumlar) {
    await t.deger(({ d, svg }) => { document.getElementById("vt-keskin-ab")?.remove(); document.getElementById("__ab")?.remove();
      if (d === null) return;
      const e = document.createElement("style"); e.id = "__ab";
      if (d === "yok") e.textContent = ".vt-hero img.vt-hero__poster, .vt-hero video { filter: none !important; }";
      else { document.querySelector("svg.vt-hero__filtre").insertAdjacentHTML("beforeend", svg); e.textContent = ".vt-hero img.vt-hero__poster, .vt-hero video { filter: url(#vt-keskin-ab) !important; }"; }
      document.head.appendChild(e); }, { d, svg: d && d !== "yok" ? AYRISIK(d) : "" });
    await bekle(900);
    const buf = await t.resim(kutu);
    resim[ad] = PNG.sync.read(Buffer.from(buf));
    fs.writeFileSync(path.join(cikti, `${kip}-${surucu}-${gAd}-${ad.replace("/", "_")}.png`), Buffer.from(buf));
  }
  const kiyas = (a, b, kenar) => {                           // kenar: dış çerçeveden kaç aygıt pikseli hariç
    if (a.width !== b.width || a.height !== b.height) return { boyut: [a.width, a.height, b.width, b.height] };
    let enBuyuk = 0, f1 = 0, f2 = 0, f3 = 0, n = 0; const hist = {};
    for (let y = kenar; y < a.height - kenar; y++) for (let x = kenar; x < a.width - kenar; x++) {
      const i = (y * a.width + x) * 4; const d = Math.max(Math.abs(a.data[i] - b.data[i]), Math.abs(a.data[i + 1] - b.data[i + 1]), Math.abs(a.data[i + 2] - b.data[i + 2]));
      n++; enBuyuk = Math.max(enBuyuk, d); if (d > 1) f1++; if (d > 2) f2++; if (d > 4) f3++; hist[Math.min(d, 9)] = (hist[Math.min(d, 9)] || 0) + 1;
    }
    return { piksel: n, enBuyuk, ">1": f1 / n, ">2": f2 / n, ">4": f3 / n, hist };
  };
  const r = { surucu, surum: t.surum, gorunum: gAd, kutu, kiyas: {} };
  for (const [ad] of durumlar.slice(1)) r.kiyas[ad] = { tum: kiyas(resim.ozgun, resim[ad], 0), ic: kiyas(resim.ozgun, resim[ad], 4) };
  sonuc.push(r);
  console.log(`${surucu} ${t.surum} ${gAd} poster tamam=${kutu.tamam} filtre=${kutu.filtre}`);
  for (const [ad, k] of Object.entries(r.kiyas)) console.log(`   ${ad.padEnd(15)} tüm: en büyük ${k.tum.enBuyuk} · >1 %${(100 * k.tum[">1"]).toFixed(3)} · >2 %${(100 * k.tum[">2"]).toFixed(3)} | iç (kenar 4 px hariç): en büyük ${k.ic.enBuyuk} · >1 %${(100 * k.ic[">1"]).toFixed(3)} · >2 %${(100 * k.ic[">2"]).toFixed(3)}`);
  await t.kapat();
}
fs.writeFileSync(path.join(cikti, `esdeger-${kip}.json`), JSON.stringify(sonuc, null, 1));
