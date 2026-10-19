// ab-yukleme.mjs — Faz 2 A/B: yükleme yolu. «mevcut» ile «videosuz» (aynı derleme; kenar sunucu *.mp4 → 404) karşılaştırılır.
// node olc/ab-yukleme.mjs [--motor chromium,firefox,webkit] [--gorunum 1440x900,390x844] [--ag yavas4g,hizli3g] [--kosu 3] [--cikti analiz/ab]
// Her koşu: yeni bağlam → SOĞUK yükleme, 20 sn gözlem → about:blank + hat boşalır → SICAK yükleme, 12 sn gözlem.
// Ölçülenler: FCP, tüm LCP adayları, poster ve her levhanın (Storyset PNG) yüklenme anı, video «playing» anı,
// hattan geçen bayt (vekil sayacı: süren medya indirmeleri dahil; motor bağımsız) load / +5 / +10 / +20 sn'de,
// indirilen font dosyaları, sıcak yüklemede yavaş-hat kaydı (localStorage pvq_yavas_hat) ve videonun inip inmediği.
import fs from "node:fs";
import path from "node:path";
import { KOK, GORUNUMLER, motorAc, baglamAyar, OLCUM_BETIGI } from "./ortak.mjs";

const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const PORT_ANAHTAR = () => (arg("hedef", "once") === "sonra" ? { mevcut: 1 } : { mevcut: 1, videosuz: 1 });
const motorlar = arg("motor", "chromium,firefox,webkit").split(",");
const gorunumler = arg("gorunum", "1440x900,390x844").split(",");
const aglar = arg("ag", "yavas4g,hizli3g").split(",");
const degiskenler = arg("degisken", Object.keys(PORT_ANAHTAR()).join(",")).split(",");
const kosu = Number(arg("kosu", "3"));
const cikti = path.join(KOK, arg("cikti", "analiz/ab"));
fs.mkdirSync(cikti, { recursive: true });
const dosya = path.join(cikti, "yukleme.jsonl");
const hedef = arg("hedef", "once");
const PORT = hedef === "sonra" ? { mevcut: { hizli3g: 29443, yavas4g: 30443, seffaf: 31443, kablo20: 32443 } }
  : { mevcut: { hizli3g: 19443, yavas4g: 20443, seffaf: 21443, kablo20: 22443 }, videosuz: { hizli3g: 19445, yavas4g: 20445, seffaf: 21445, kablo20: 22445 } };
const yapilan = new Set(fs.existsSync(dosya) ? fs.readFileSync(dosya, "utf8").trim().split("\n").filter(Boolean).map((s) => JSON.parse(s).anahtar) : []);
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
const denetim = (port) => fetch(`http://127.0.0.1:${port + 1}/`).then((r) => r.json());
async function hatBos(port) {
  const bas = Date.now(); let bos = 0;
  while (Date.now() - bas < 120000) { const d = await denetim(port).catch(() => null); if (d && d.kuyruk <= 0 && d.asagiMs <= 0) { if ((bos += 250) >= 750) return; } else bos = 0; await bekle(250); }
}

const IZ = `(() => {
  const a = window.__ab = { img: {}, oynadi: null, vbas: null, vhata: null };
  document.addEventListener("load", (e) => { const t = e.target; if (t && t.tagName === "IMG") a.img[(t.currentSrc || t.src).split("/").pop()] = performance.now(); }, true);
  document.addEventListener("loadstart", (e) => { if (e.target && e.target.tagName === "VIDEO" && a.vbas === null) a.vbas = performance.now(); }, true);
  document.addEventListener("playing", (e) => { if (e.target && e.target.tagName === "VIDEO" && a.oynadi === null) a.oynadi = performance.now(); }, true);
  document.addEventListener("error", (e) => { if (e.target && (e.target.tagName === "SOURCE" || e.target.tagName === "VIDEO") && a.vhata === null) a.vhata = performance.now(); }, true);
})();`;

const durum = (s) => s.evaluate(() => {
  const r = performance.getEntriesByType("resource"); const p = Object.fromEntries(performance.getEntriesByType("paint").map((e) => [e.name, e.startTime]));
  const n = performance.getEntriesByType("navigation")[0] || {}; const v = document.querySelector("video.vt-hero__video");
  return { fcp: p["first-contentful-paint"] ?? null, load: n.loadEventEnd ?? null, lcp: (window.__olc?.lcp || []).map((x) => ({ t: Math.round(x.t), boy: x.boy, el: x.el })),
    img: Object.fromEntries(Object.entries(window.__ab?.img || {}).map(([k, t]) => [k, Math.round(t)])), oynadi: window.__ab?.oynadi ?? null, vbas: window.__ab?.vbas ?? null, vhata: window.__ab?.vhata ?? null,
    font: r.filter((e) => /\.woff2/.test(e.name)).map((e) => ({ u: e.name.split("/").pop(), bas: Math.round(e.startTime), bit: Math.round(e.responseEnd), b: e.transferSize })),
    video: v ? { kaynak: (v.currentSrc || "").split("/").pop(), ag: v.networkState, hazir: v.readyState, durdu: v.paused, t: v.currentTime, tampon: v.buffered.length ? v.buffered.end(v.buffered.length - 1) : 0 } : null,
    yavasKayit: (() => { try { return localStorage.getItem("pvq_yavas_hat"); } catch { return "erişilemedi"; } })() };
});

async function yukle(s, url, port, pencere) {
  await s.goto("about:blank").catch(() => {});
  await hatBos(port);
  const b0 = (await denetim(port)).asagiBayt;
  const t0 = Date.now();
  let hata = null;
  try { await s.goto(url, { waitUntil: "load", timeout: 180000 }); } catch (e) { hata = String(e.message).split("\n")[0]; }
  const loadSn = (Date.now() - t0) / 1000;
  const bayt = { load: (await denetim(port)).asagiBayt - b0 };
  for (const an of pencere) { const kalan = an * 1000 - (Date.now() - t0) + loadSn * 1000; if (kalan > 0) await bekle(kalan); bayt["+" + an] = (await denetim(port)).asagiBayt - b0; }
  return { hata, loadSn, bayt, ...(await durum(s)) };
}

for (const motor of motorlar) {
  const tarayici = await motorAc(motor, hedef);
  for (const gAd of gorunumler) for (const ag of aglar) for (const d of degiskenler) for (let k = 1; k <= kosu; k++) {
    const anahtar = [hedef, motor, gAd, ag, d, k].join("|");
    if (yapilan.has(anahtar)) continue;
    const port = PORT[d][ag];
    const baglam = await tarayici.newContext(baglamAyar(motor, GORUNUMLER[gAd]));
    await baglam.addInitScript(OLCUM_BETIGI); await baglam.addInitScript(IZ);
    const s = await baglam.newPage();
    const soguk = await yukle(s, `https://localhost:${port}/`, port, [5, 10, 20]);
    const sicak = await yukle(s, `https://localhost:${port}/`, port, [5, 12]);
    await baglam.close();
    const satir = { anahtar, hedef, motor, surum: tarayici.version(), gorunum: gAd, ag, degisken: d, kosu: k, zaman: new Date().toISOString(), soguk, sicak };
    fs.appendFileSync(dosya, JSON.stringify(satir) + "\n");
    const levha = (x) => { const t = Object.entries(x.img).filter(([u]) => u.endsWith(".png")).map(([, t]) => t); return t.length ? `${t.length} levha son ${Math.max(...t)}` : "levha yok"; };
    console.log(`${motor} ${gAd} ${ag} ${d} #${k} · soğuk: LCP ${soguk.lcp.at(-1)?.t ?? "-"} oynadı ${soguk.oynadi?.toFixed(0) ?? "-"} ${levha(soguk)} bayt+10 ${(soguk.bayt["+10"] / 1e6).toFixed(2)} MB · sıcak: oynadı ${sicak.oynadi?.toFixed(0) ?? "-"} bayt+12 ${(sicak.bayt["+12"] / 1e6).toFixed(2)} MB kayıt ${sicak.yavasKayit}`);
  }
  await tarayici.close();
}
console.log("bitti:", dosya);
