// 26.10 görsel uyum turu — İKİ PANEL ÖLÇÜMÜ (Playwright, channel chrome): hesaplanmış stil + yazı tipi histogramı + taşma + kare.
// Ön koşul: sahte API 4807 (PLATFORM_2FA=1 node sahte-api.mjs 4807), vite preview 4273 (VITE_API_URL=http://127.0.0.1:4807 derlemesi).
// Kullanım: node iki-panel-olcum.mjs <çıktı-dizini> [genişlikler=1440] [kare=1]; müşteri paneli örnek kip (pvq_token=ornek-kip), platform sahte jeton.
import { chromium } from "playwright"; import fs from "node:fs";
const [cikti, genArg, kareArg] = process.argv.slice(2); const GEN = (genArg ?? "1440").split(",").map(Number); const KARE = kareArg !== "0";
const BASE = "http://127.0.0.1:4273"; fs.mkdirSync(cikti, { recursive: true });
const PJ = "x." + Buffer.from('{"sub":"p1","kapsam":"platform","rol":"sahip","sv":0}').toString("base64url") + ".y";
const MUSTERI = ["Portföy", "Santralim", "Tahminler", "Raporlar", "Ayarlar"];
const PLATFORM = ["Genel bakış", "Sistem", "Müşteriler", "Kullanım", "Kullanıcılar", "Başvurular", "Denetim izi", "Operatörler", "Planlar", "Hesabım"];
const SEC = ["h1", ".sayfa-bas p", ".kart", ".kart-bas h3", ".kart-alt", ".kpi", ".kpi-et", ".kpi-dg", ".kpi-br", "table.veri", "table.veri th", "table.veri td", "table.veri td.ad",
  ".rozet", ".cip", ".cip-kod", ".dugme", ".dugme.kucuk", ".girdi", ".girdi-etiket", ".nav-btn", ".ust", ".icerik", ".zaman", ".mono", "body", ".yan", ".kod", ".plat-saglik", ".plat-ayrinti__cip"];
const OLC = (secler) => {
  const al = (e) => { const cs = getComputedStyle(e); const r = e.getBoundingClientRect(); return { ff: cs.fontFamily.split(",")[0].replace(/['"]/g, ""), fs: cs.fontSize, fw: cs.fontWeight, lh: cs.lineHeight, ls: cs.letterSpacing,
    fvn: cs.fontVariantNumeric, c: cs.color, bg: cs.backgroundColor, bc: cs.borderTopColor, br: cs.borderRadius, p: cs.padding, h: Math.round(r.height), w: Math.round(r.width), tt: cs.textTransform }; };
  const out = {}; for (const s of secler) { const e = document.querySelector(s); if (e) out[s] = al(e); }
  const aileler = {}; let n = 0;
  for (const e of document.querySelectorAll("body *")) { if (n++ > 8000) break; if (!e.textContent || !e.textContent.trim()) continue;
    if (e.children.length && [...e.childNodes].every((c) => c.nodeType !== 3 || !c.textContent.trim())) continue;
    const cs = getComputedStyle(e); if (cs.display === "none" || cs.visibility === "hidden") continue;
    const k = cs.fontFamily.split(",")[0].replace(/['"]/g, "") + " " + cs.fontWeight + " " + cs.fontSize; aileler[k] = (aileler[k] ?? 0) + 1; }
  const de = document.documentElement;
  const tasan = [...document.querySelectorAll("body *")].filter((e) => { const r = e.getBoundingClientRect(); return r.right > de.clientWidth + 1 && getComputedStyle(e).position !== "fixed"; }).slice(0, 5).map((e) => e.className?.toString().slice(0, 40) || e.tagName);
  return { stiller: out, aileler, tasma: de.scrollWidth - de.clientWidth, tasan, yukseklik: de.scrollHeight, iskelet: document.querySelectorAll(".iskelet, .iskelet-alan").length, hata: document.querySelectorAll("[role=alert]").length, tema: de.dataset.tema, yuz: de.dataset.yuz };
};
const tarayici = await chromium.launch({ channel: "chrome", headless: true });
const rapor = {}; const hatalar = [];
for (const w of GEN) {
  const ctx = await tarayici.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 1, reducedMotion: "reduce", isMobile: w < 768, hasTouch: w < 768 });
  const sayfa = await ctx.newPage(); sayfa.on("pageerror", (e) => hatalar.push(`${w}: ${e.message}`)); sayfa.on("console", (m) => { if (m.type() === "error") hatalar.push(`${w} console: ${m.text().slice(0, 120)}`); });
  const tur = async (ad, yol, sayfalar, hazirla, arg) => {
    await sayfa.goto(BASE + yol); await sayfa.evaluate(hazirla, arg); await sayfa.goto(BASE + yol); await sayfa.waitForSelector(".nav-btn", { timeout: 15000 });
    for (const s of sayfalar) {
      if (w < 900) { await sayfa.click(".menu-dugme"); await sayfa.waitForTimeout(300); }
      const ok = await sayfa.evaluate((s) => { const b = [...document.querySelectorAll(".nav-btn")].find((b) => b.textContent.trim() === s); if (!b) return false; b.click(); return true; }, s);
      if (!ok) { hatalar.push(`${ad}/${s}@${w}: nav yok`); continue; }
      await sayfa.waitForTimeout(1200); await sayfa.evaluate(() => document.fonts.ready); await sayfa.evaluate(() => window.scrollTo(0, 0));
      const o = await sayfa.evaluate(OLC, SEC); rapor[`${ad}/${s}@${w}`] = o;
      process.stdout.write(`${ad}/${s}@${w}: taşma ${o.tasma} · iskelet ${o.iskelet} · alert ${o.hata} · ${o.yukseklik}px\n`);
      if (KARE) await sayfa.screenshot({ path: `${cikti}/${ad}-${s.replace(/\s/g, "_").toLowerCase()}-${w}.png`, fullPage: true });
    }
  };
  await tur("musteri", "/", MUSTERI, () => { localStorage.setItem("pvq_token", "ornek-kip"); localStorage.setItem("pvq_tema", "koyu"); });
  await tur("platform", "/yonetim", PLATFORM, (pj) => { localStorage.setItem("pvq_platform_token", pj); }, PJ);
  await ctx.close();
}
fs.writeFileSync(`${cikti}/rapor.json`, JSON.stringify({ rapor, hatalar }, null, 1));
console.log("hatalar:", hatalar.length, hatalar.slice(0, 10).join(" | "));
await tarayici.close();
