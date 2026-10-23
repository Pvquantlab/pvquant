/** Üç motor (Chromium / Firefox / WebKit) panel + vitrin sınaması — Playwright (scratchpad'e `npm i playwright`,
 *  tarayıcılar ~/Library/Caches/ms-playwright). Kullanım:
 *    node motor-test.mjs <base-url> <çıktı-dizini> [motorlar=chromium,firefox,webkit] [canlı-vitrin-url]
 *  Örnek kip üretim derlemesi: sahte jetonla panel, SAHTE_ZAMAN ile grafik dolu. Her motorda 1440 ve 375 px:
 *  9 sayfa (h1 + hazır işareti), konsol/sayfa hataları (örnek kip `undefined/v1` 404'leri ayıklanır), yatay taşma,
 *  geçiş süresi; etkileşimler: tema düğmeleri, details, kopyala çipi, grafik tooltip; CSS destekleri (:has, clip-path).
 *  Kareler: Portföy/Santralim/Doğruluk koyu 1440 + Portföy açık 1440 + Tahminler 375. Sayı uydurulmaz. */
import fs from "node:fs";
import { createRequire } from "node:module";
const require = createRequire(process.env.PW_DIR ? process.env.PW_DIR + "/" : import.meta.url);
const pw = require("playwright");
const [base, dizin, motorArg, vitrinUrl] = process.argv.slice(2);
if (!base || !dizin) { console.error("kullanım: node motor-test.mjs <base> <dizin> [motorlar] [vitrin-url]"); process.exit(2); }
const MOTORLAR = (motorArg ?? "chromium,firefox,webkit").split(",");
const SAYFALAR = ["Portföy", "Santralim", "Veri yükleme", "Kalibrasyon", "Tahminler", "Doğruluk", "Aylık beklenti", "Raporlar", "Hakkında"];
fs.mkdirSync(dizin, { recursive: true });
const SAHTE = process.env.SAHTE_ZAMAN ?? "2026-08-01T12:30:00+03:00";
const rapor = {};
for (const motor of MOTORLAR) {
  const t = { surum: null, hatalar: [], sayfalar: {}, etkilesim: {}, css: {}, vitrin: null };
  const tarayici = await pw[motor].launch({ headless: true });
  t.surum = tarayici.version();
  for (const gen of [1440, 375]) {
    const ctx = await tarayici.newContext({ viewport: { width: gen, height: gen < 768 ? 812 : 900 }, locale: "tr-TR", timezoneId: "Europe/Istanbul" });
    await ctx.addInitScript((hedef) => {
      const KAYMA = new Date(hedef).getTime() - Date.now(); const G = Date;
      class SahteDate extends G { constructor(...a) { a.length === 0 ? super(G.now() + KAYMA) : super(...a); } static now() { return G.now() + KAYMA; } }
      window.Date = SahteDate;
    }, SAHTE);
    await ctx.addInitScript(() => { localStorage.setItem("pvq_token", "ornek-kip"); localStorage.setItem("pvq_tema", "koyu"); });
    const sayfa = await ctx.newPage();
    const hatalar = [];
    sayfa.on("console", (m) => { if (m.type() === "error" && !/undefined\/v1\//.test(m.text()) && !/404/.test(m.text())) hatalar.push(`${gen}: konsol: ${m.text().slice(0, 140)}`); });
    sayfa.on("pageerror", (e) => hatalar.push(`${gen}: istisna: ${String(e.message).slice(0, 140)}`));
    sayfa.on("requestfailed", (r) => { if (!/undefined\/v1\//.test(r.url())) hatalar.push(`${gen}: istek düştü: ${r.url().split("/").slice(-2).join("/")} ${r.failure()?.errorText ?? ""}`); });
    // Jeton ve tema init-script ile: vitrin yüklenirken ikinci gezinme yapmak WebKit'te iptal edilen tembel parçadan
    // «React #306» ve Firefox'ta NS_BINDING_ABORTED görsel istekleri üretir (sınama kaynaklı, uygulama hatası değil).
    // Sunucu portu: Firefox 4190'ı (sieve) yasaklı port sayar → 4273 gibi bir port; python http.server de Firefox'ta kesilir, vite preview kullan.
    await sayfa.goto(base + "/", { waitUntil: "load" });
    await sayfa.waitForSelector(".nav-btn", { timeout: 15000 });
    await sayfa.waitForTimeout(800);
    if (gen === 1440) t.css = await sayfa.evaluate(() => ({
      has: CSS.supports("selector(:has(input))"), clipPath: CSS.supports("clip-path", "inset(0 0 0 19px)"),
      io: typeof IntersectionObserver === "function", ric: typeof requestIdleCallback === "function",
      tema: document.documentElement.dataset.tema ?? "(yok)", ua: navigator.userAgent.slice(0, 80) }));
    for (const s of SAYFALAR) {
      const r = await sayfa.evaluate(async (hedef) => {
        const t0 = performance.now();
        const h1once = document.querySelector(".icerik h1")?.textContent ?? "";
        [...document.querySelectorAll(".nav-btn")].find((b) => b.textContent.trim() === hedef)?.click();
        let hazir = null; const bitis = t0 + 10000;
        while (performance.now() < bitis) {
          await new Promise((r) => requestAnimationFrame(r));
          const ic = document.querySelector(".icerik"); const h1 = ic?.querySelector("h1")?.textContent ?? "";
          if (h1 && h1 !== h1once && !/Yükleniyor/.test(ic.textContent) && ic.querySelector(".kart, .kpi, .bos-durum, table")) { hazir = performance.now() - t0; break; }
        }
        await new Promise((r) => setTimeout(r, 300));
        const de = document.documentElement;
        return { hazir: hazir == null ? null : Math.round(hazir), tasma: Math.max(0, de.scrollWidth - de.clientWidth), h1: document.querySelector(".icerik h1")?.textContent ?? "", kart: document.querySelectorAll(".icerik .kart").length, tuval: document.querySelectorAll(".icerik canvas").length };
      }, s);
      t.sayfalar[`${s}@${gen}`] = r;
      // v2.474 tembel grafik: görünür olmayan tuval başlamaz → tam sayfa kareden önce sona kaydır, geri dön
      await sayfa.evaluate(async () => { window.scrollTo(0, document.body.scrollHeight); await new Promise((r) => setTimeout(r, 700)); window.scrollTo(0, 0); await new Promise((r) => setTimeout(r, 250)); });
      if (gen === 1440 && ["Portföy", "Santralim", "Doğruluk"].includes(s)) await sayfa.screenshot({ path: `${dizin}/${motor}-${s.replace(/\s/g, "_").toLowerCase()}-1440.png`, fullPage: true });
      if (gen === 375 && s === "Tahminler") await sayfa.screenshot({ path: `${dizin}/${motor}-tahminler-375.png`, fullPage: true });
    }
    if (gen === 1440) {
      // etkileşimler
      const e = {};
      await sayfa.evaluate(() => [...document.querySelectorAll(".nav-btn")].find((b) => b.textContent.trim() === "Tahminler").click()); await sayfa.waitForTimeout(800);
      const det = sayfa.locator("details.aciklama summary").first(); await det.click(); await sayfa.waitForTimeout(200);
      e.details = await sayfa.evaluate(() => document.querySelector("details.aciklama")?.open === true);
      const tuval = sayfa.locator(".icerik canvas").first(); const kutu = await tuval.boundingBox();
      if (kutu) { await sayfa.mouse.move(kutu.x + kutu.width * 0.3, kutu.y + kutu.height * 0.45); await sayfa.waitForTimeout(500);
        e.tooltip = await sayfa.evaluate(() => { const d = [...document.querySelectorAll("div")].find((x) => /z-index:\s*9999999/.test(x.getAttribute("style") || "")); return d ? d.innerText.slice(0, 60).replace(/\n/g, " | ") : "yok"; }); }
      await sayfa.evaluate(() => [...document.querySelectorAll("button")].find((b) => b.textContent.trim() === "Açık")?.click()); await sayfa.waitForTimeout(300);
      e.temaAcik = await sayfa.evaluate(() => document.documentElement.dataset.tema);
      await sayfa.screenshot({ path: `${dizin}/${motor}-tahminler-acik-1440.png`, fullPage: false });
      await sayfa.evaluate(() => [...document.querySelectorAll("button")].find((b) => b.textContent.trim() === "Koyu")?.click()); await sayfa.waitForTimeout(300);
      e.temaKoyu = await sayfa.evaluate(() => document.documentElement.dataset.tema);
      await sayfa.evaluate(() => [...document.querySelectorAll(".nav-btn")].find((b) => b.textContent.trim() === "Portföy").click()); await sayfa.waitForTimeout(800);
      const uc = sayfa.locator(".uc-kopyala").first();
      if (await uc.count()) { await uc.click(); await sayfa.waitForTimeout(300); e.kopyala = await sayfa.evaluate(() => document.querySelector(".uc-kopyala .uc-geri")?.textContent || "(boş)"); }
      e.metaAyrac = await sayfa.evaluate(() => { const m = document.querySelector(".cip .meta"); if (!m) return "yok"; const cs = getComputedStyle(m); const ilk = m.children[0]; const r = getComputedStyle(ilk, "::before"); return `clip=${cs.clipPath} before=${r.position}/${r.left}`; });
      t.etkilesim = e;
      // Portföy açık tema karesi
      await sayfa.evaluate(() => { document.documentElement.dataset.tema = "acik"; }); await sayfa.waitForTimeout(200);
      await sayfa.screenshot({ path: `${dizin}/${motor}-portföy-acik-1440.png`, fullPage: true });
    }
    t.hatalar.push(...hatalar);
    await ctx.close();
  }
  if (vitrinUrl) {
    const ctx = await tarayici.newContext({ viewport: { width: 1440, height: 900 }, locale: "tr-TR" });
    const sayfa = await ctx.newPage(); const vh = [];
    sayfa.on("pageerror", (e) => vh.push(String(e.message).slice(0, 120)));
    sayfa.on("console", (m) => { if (m.type() === "error") vh.push("konsol: " + m.text().slice(0, 120)); });
    await sayfa.goto(vitrinUrl, { waitUntil: "load", timeout: 60000 }); await sayfa.waitForTimeout(2500);
    const v = await sayfa.evaluate(() => { const de = document.documentElement; return { tasma: Math.max(0, de.scrollWidth - de.clientWidth), h1: document.querySelector("h1")?.textContent?.slice(0, 60), fontlar: [...document.fonts].filter((f) => f.status === "loaded").length }; });
    await sayfa.screenshot({ path: `${dizin}/${motor}-vitrin-1440.png`, fullPage: false });
    await sayfa.setViewportSize({ width: 375, height: 812 }); await sayfa.waitForTimeout(800);
    v.tasma375 = await sayfa.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth));
    v.hatalar = vh; t.vitrin = v; await ctx.close();
  }
  await tarayici.close();
  rapor[motor] = t;
  const sy = Object.entries(t.sayfalar);
  console.log(`\n== ${motor} ${t.surum} · ${t.css.ua ?? ""}`);
  console.log(`   css: :has ${t.css.has} · clip-path ${t.css.clipPath} · IO ${t.css.io} · rIC ${t.css.ric} · ilk data-tema ${t.css.tema}`);
  console.log(`   hazır(ms)/taşma  ` + sy.map(([k, v]) => `${k}=${v.hazir}/${v.tasma}`).join("  "));
  console.log(`   kart/tuval 1440: ` + sy.filter(([k]) => k.endsWith("@1440")).map(([k, v]) => `${k.split("@")[0]}:${v.kart}/${v.tuval}`).join(" "));
  console.log(`   etkileşim: ${JSON.stringify(t.etkilesim)}`);
  console.log(`   hatalar: ${t.hatalar.length}${t.hatalar.length ? "\n     " + [...new Set(t.hatalar)].slice(0, 6).join("\n     ") : ""}`);
  if (t.vitrin) console.log(`   vitrin: taşma 1440=${t.vitrin.tasma} 375=${t.vitrin.tasma375} · h1 «${t.vitrin.h1}» · fontlar ${t.vitrin.fontlar} · hata ${t.vitrin.hatalar.length}${t.vitrin.hatalar.length ? ": " + t.vitrin.hatalar.slice(0, 3).join(" | ") : ""}`);
}
fs.writeFileSync(`${dizin}/rapor.json`, JSON.stringify(rapor, null, 2));
console.log(`\nyazıldı ${dizin}/rapor.json`);
