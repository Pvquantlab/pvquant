// ab-boya.mjs — Faz 2 A/B: hero oynarken ve kaydırırken boya/birleştirme maliyeti; değişken başına aynı sayfa üzerinde.
// node olc/ab-boya.mjs --surucu pw-firefox,chrome,firefox-stok --gorunum 1440x900,390x844 [--basli] [--kosu 3] [--hedef once] [--cikti analiz/ab]
// Sürücüler: pw-chromium | pw-firefox | pw-webkit (Playwright derlemeleri) · chrome (stok Google Chrome, Playwright kanalı) ·
//            firefox-stok (stok /Applications/Firefox.app, puppeteer-core + WebDriver BiDi).
// Değişkenler yük SONRASI uygulanır (aynı sayfa, sıra koşu başına döndürülür): sayfanın ağ/yükleme yolu değişmez, yalnız
// sürekli maliyet kıyaslanır. Bunlar TEŞHİS içindir, düzeltme değil (tasarım dokunulmaz):
//   mevcut · filtresiz (video+poster filter:none) · filtresiz-video (yalnız video) · camsiz (backdrop-filter:none) · filtresiz+camsiz · video-durgun (pause)
// Ölçülenler (pencere: 5 sn boşta + 3 sn kaydırma):
//   kare aralıkları (rAF; p50/p95, «kaçan kare» = 1,5×ortanca üstü oranı) · ana iş parçacığı tıkanması (20 ms'lik zamanlayıcı
//   zincirinin 50 ms üstü gecikmeleri toplamı; tüm motorlarda) · video: requestVideoFrameCallback sayısı ve
//   getVideoPlaybackQuality düşen kare · tarayıcı süreç ağacının CPU süresi (ps cputime farkı; GPU/içerik süreçleri dahil).
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { chromium, firefox, webkit } from "playwright";
import puppeteer from "puppeteer-core";
import { KOK, HEDEFLER, GORUNUMLER } from "./ortak.mjs";

const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const basli = process.argv.includes("--basli");
const hedef = arg("hedef", "once");
const suruculer = arg("surucu", "pw-chromium,pw-firefox,pw-webkit").split(",");
const gorunumler = arg("gorunum", "1440x900,390x844").split(",");
const kosu = Number(arg("kosu", "3"));
const cikti = path.join(KOK, arg("cikti", "analiz/ab"));
fs.mkdirSync(cikti, { recursive: true });
const dosya = path.join(cikti, "boya.jsonl");
const URL0 = HEDEFLER[hedef].yok + "/";
const spki = HEDEFLER[hedef].spki ? fs.readFileSync(path.join(KOK, HEDEFLER[hedef].spki), "utf8").trim() : null;
const yapilan = new Set(fs.existsSync(dosya) ? fs.readFileSync(dosya, "utf8").trim().split("\n").filter(Boolean).map((s) => JSON.parse(s).anahtar) : []);
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));

const CSS = {
  filtresiz: ".vt-hero video, .vt-hero img { filter: none !important; }",
  "filtresiz-video": ".vt-hero video { filter: none !important; }",
  camsiz: "*, *::before, *::after { backdrop-filter: none !important; -webkit-backdrop-filter: none !important; }",
};
const DEGISKEN = arg("degisken", "mevcut,filtresiz,filtresiz-video,camsiz,filtresiz+camsiz,video-durgun").split(",");
// Ek değişkenler (aday düzeltmeler; --degisken ile seçilir): katman = filtreli öğeleri kendi birleştirme katmanına al.
CSS.katman = ".vt-hero video, .vt-hero img.vt-hero__poster { will-change: transform; }";
// ayrisik: aynı çekirdek (o = 2,8c − 0,45·(l+r+u+d)) WebRender'ın yerel ilkelleriyle: 4 feOffset (±1 aygıt pikseli) + 3 ortalama + 1 aritmetik.
const AYRISIK_SVG = (d) => `<filter id="vt-keskin-ab" color-interpolation-filters="sRGB" x="0" y="0" width="1" height="1">
  <feOffset in="SourceGraphic" dx="${d}" dy="0" result="l"/><feOffset in="SourceGraphic" dx="-${d}" dy="0" result="r"/>
  <feOffset in="SourceGraphic" dx="0" dy="${d}" result="u"/><feOffset in="SourceGraphic" dx="0" dy="-${d}" result="a"/>
  <feComposite in="l" in2="r" operator="arithmetic" k2=".5" k3=".5" result="lr"/><feComposite in="u" in2="a" operator="arithmetic" k2=".5" k3=".5" result="ua"/>
  <feComposite in="lr" in2="ua" operator="arithmetic" k2=".5" k3=".5" result="m"/>
  <feComposite in="SourceGraphic" in2="m" operator="arithmetic" k2="2.8" k3="-1.8"/></filter>`;
CSS.ayrisik = ".vt-hero video, .vt-hero img.vt-hero__poster { filter: url(#vt-keskin-ab) !important; }";

// ── süreç ağacı CPU süresi (sn): kök pid'in torunları ∪ komut satırında işaret geçen süreçler (WebKit XPC süreçleri launchd altında)
function cpuOrnek(kokPid, isaret) {
  const satir = execFileSync("ps", ["-A", "-o", "pid=,ppid=,time=,command="], { encoding: "utf8", maxBuffer: 64 << 20 }).trim().split("\n");
  const surec = satir.map((s) => { const m = s.trim().match(/^(\d+)\s+(\d+)\s+(\S+)\s+(.*)$/); return m && { pid: +m[1], ppid: +m[2], t: m[3], cmd: m[4] }; }).filter(Boolean);
  const sn = (t) => t.split(":").map(Number).reduce((s, x) => s * 60 + x, 0);   // ps «m:ss.ss» / «h:mm:ss.ss»
  const cocuk = new Map(); for (const p of surec) { if (!cocuk.has(p.ppid)) cocuk.set(p.ppid, []); cocuk.get(p.ppid).push(p); }
  const sec = new Map(); const yigin = [kokPid];
  while (yigin.length) { const k = yigin.pop(); for (const c of cocuk.get(k) || []) if (!sec.has(c.pid)) { sec.set(c.pid, c); yigin.push(c.pid); } }
  if (isaret) for (const p of surec) if (p.cmd.includes(isaret) && p.pid !== process.pid) sec.set(p.pid, p);
  sec.delete(process.pid);
  return new Map([...sec.values()].map((p) => [p.pid, sn(p.t)]));
}
const cpuFark = (a, b) => { let s = 0; for (const [pid, t] of b) s += t - (a.get(pid) ?? 0); return s; };

// ── sürücü soyutlaması
async function ac(surucu, g) {
  if (surucu === "firefox-stok") {
    const t = await puppeteer.launch({ browser: "firefox", executablePath: "/Applications/Firefox.app/Contents/MacOS/firefox", headless: !basli, acceptInsecureCerts: true, defaultViewport: null });
    const surum = await t.version();
    return {
      surum, kokPid: t.process().pid, isaret: null,
      async sayfa() { const b = await t.createBrowserContext(); const s = await b.newPage(); await s.setViewport({ width: g.width, height: g.height, deviceScaleFactor: g.dpr });
        return { git: (u) => s.goto(u, { waitUntil: "load", timeout: 120000 }), deger: (f, a) => s.evaluate(f, a), kapat: () => b.close() }; },
      kapat: () => t.close(),
    };
  }
  const motor = { "pw-chromium": chromium, chrome: chromium, "pw-firefox": firefox, "pw-webkit": webkit }[surucu];
  const secenek = { headless: !basli, args: [] };
  if (surucu === "chrome") secenek.channel = "chrome";
  if ((surucu === "pw-chromium" || surucu === "chrome") && spki) secenek.args.push("--ignore-certificate-errors-spki-list=" + spki);
  const t = await motor.launch(secenek);
  const isaret = surucu === "pw-webkit" ? "ms-playwright/webkit" : null;
  return {
    surum: t.version(), kokPid: process.pid, isaret,
    async sayfa() {
      const ayar = { viewport: { width: g.width, height: g.height }, deviceScaleFactor: g.dpr, ignoreHTTPSErrors: true };
      if (g.mobil) { ayar.hasTouch = true; if (motor !== firefox) ayar.isMobile = true; }
      const b = await t.newContext(ayar); const s = await b.newPage();
      return { git: (u) => s.goto(u, { waitUntil: "load", timeout: 120000 }), deger: (f, a) => s.evaluate(f, a), kapat: () => b.close() };
    },
    kapat: () => t.close(),
  };
}

// ── sayfa içi ölçüm (string değil fonksiyon: Playwright ve puppeteer ikisi de serileştirir)
async function pencere({ sure, kaydir }) {
  const v = document.querySelector("video.vt-hero__video");
  const q = () => { try { const x = v?.getVideoPlaybackQuality?.(); return x ? { top: x.totalVideoFrames, dus: x.droppedVideoFrames } : null; } catch { return null; } };
  const q0 = q();
  const bas = performance.now();
  let rvfc = 0; const rvfcVar = !!v?.requestVideoFrameCallback;
  if (rvfcVar && !v.paused) { const f = () => { rvfc++; if (performance.now() - bas < sure) v.requestVideoFrameCallback(f); }; v.requestVideoFrameCallback(f); }
  let tikanma = 0, enUzun = 0, beklenen = bas + 20;
  const tm = () => { const s = performance.now(); const gec = s - beklenen; if (gec > 50) tikanma += gec - 50; enUzun = Math.max(enUzun, gec); beklenen = s + 20; if (s - bas < sure) setTimeout(tm, 20); };
  setTimeout(tm, 20);
  const d = []; let onceki = null; const y0 = scrollY;
  await new Promise((res) => { const f = (t) => { if (onceki !== null) d.push(t - onceki); onceki = t; if (kaydir) scrollTo(0, y0 + (performance.now() - bas) * 0.9); if (performance.now() - bas < sure) requestAnimationFrame(f); else res(); }; requestAnimationFrame(f); });
  const q1 = q();
  d.sort((a, z) => a - z);
  const yuz = (p) => d[Math.min(d.length - 1, Math.floor(p * d.length))];
  const ort = yuz(0.5);
  return { kare: d.length, fps: d.length / (sure / 1000), p50: ort, p95: yuz(0.95), p99: yuz(0.99), kacan: d.filter((x) => x > 1.5 * ort).length / Math.max(1, d.length),
    tikanma, enUzunGecikme: enUzun, videoOynuyor: !!v && !v.paused, videoKare: rvfcVar ? rvfc : null,
    videoKalite: q0 && q1 ? { gosterilen: q1.top - q0.top, dusen: q1.dus - q0.dus } : null };
}

for (const surucu of suruculer) for (const gAd of gorunumler) {
  const g = GORUNUMLER[gAd];
  const t = await ac(surucu, g);
  for (let k = 1; k <= kosu; k++) {
    const anahtar = [hedef, surucu, basli ? "basli" : "bassiz", gAd, k].join("|");
    if (yapilan.has(anahtar)) continue;
    const s = await t.sayfa();
    await s.git(URL0); await s.git(URL0);                         // ısıt + sıcak yükleme (ağ değil boya ölçülür)
    const oynadi = await s.deger(async () => { const v = document.querySelector("video.vt-hero__video"); const b = performance.now();
      while (performance.now() - b < 20000) { if (v && !v.paused && v.readyState >= 3 && v.currentTime > 6.6) return true; await new Promise((r) => setTimeout(r, 100)); } return false; });
    await bekle(4000);                                             // poster erimesi (900 ms) + açılış artığı (ilk tampon, çözücü ısınması) geçsin
    const sira = DEGISKEN.slice(k - 1).concat(DEGISKEN.slice(0, k - 1));   // koşu başına döndürülmüş sıra
    const sonuc = {};
    for (const d of sira) {
      await s.deger(({ css, svg }) => { scrollTo(0, 0); document.getElementById("__ab")?.remove(); document.getElementById("vt-keskin-ab")?.remove();
        if (svg) document.querySelector("svg.vt-hero__filtre")?.insertAdjacentHTML("beforeend", svg);
        if (css) { const e = document.createElement("style"); e.id = "__ab"; e.textContent = css; document.head.appendChild(e); }
        const v = document.querySelector("video.vt-hero__video"); if (v && v.paused) v.play().catch(() => {}); },
        { css: d === "filtresiz+camsiz" ? CSS.filtresiz + CSS.camsiz : CSS[d] || "", svg: d === "ayrisik" ? AYRISIK_SVG((1.001 / g.dpr).toFixed(4)) : "" });
      await bekle(1200);                                           // görünürlük gözlemcisi başa dönüşü işlesin
      if (d === "video-durgun") { await s.deger(() => document.querySelector("video.vt-hero__video")?.pause()); await bekle(300); }
      const c0 = cpuOrnek(t.kokPid, t.isaret);
      const bosta = await s.deger(pencere, { sure: 5000, kaydir: false });
      const c1 = cpuOrnek(t.kokPid, t.isaret);
      const kaydirma = await s.deger(pencere, { sure: 3000, kaydir: true });
      const c2 = cpuOrnek(t.kokPid, t.isaret);
      sonuc[d] = { bosta: { ...bosta, cpu: cpuFark(c0, c1) / 5 }, kaydirma: { ...kaydirma, cpu: cpuFark(c1, c2) / 3 } };   // cpu: çekirdek-sn / sn
    }
    await s.kapat();
    const satir = { anahtar, hedef, surucu, surum: t.surum, mod: basli ? "basli" : "bassiz", gorunum: gAd, kosu: k, zaman: new Date().toISOString(), oynadi, sira, sonuc };
    fs.appendFileSync(dosya, JSON.stringify(satir) + "\n");
    console.log(`${surucu} ${basli ? "başlı" : "başsız"} ${gAd} #${k} oynadı=${oynadi} · ` + DEGISKEN.map((d) => `${d}: p95 ${sonuc[d].bosta.p95?.toFixed(1)} kaçan %${(100 * sonuc[d].bosta.kacan).toFixed(0)} cpu ${sonuc[d].bosta.cpu.toFixed(2)} vkare ${sonuc[d].bosta.videoKare ?? "-"}`).join(" | "));
  }
  await t.kapat();
}
console.log("bitti:", dosya);
