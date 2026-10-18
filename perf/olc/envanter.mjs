// envanter.mjs — pahalı birleştirme özellikleri envanteri: backdrop-filter, filter, mix-blend-mode, mask, opacity<1 katmanlar.
// node olc/envanter.mjs --hedef once --cikti baseline   → <cikti>/envanter.json + konsol özeti
// Her motor × görünüm × sayfa: ilgili özelliği taşıyan öğe (ve ::before/::after) sayısı, toplam alan (CSS px²) ve
// ilk ekranla kesişen alan; ilk ekran alanına oranı. Sayfa kısıtsız ağda, sıcak önbellekle açılır.
import fs from "node:fs";
import path from "node:path";
import { KOK, HEDEFLER, GORUNUMLER, SAYFALAR, motorAc, baglamAyar } from "./ortak.mjs";

const arg = (ad, vars) => { const i = process.argv.indexOf("--" + ad); return i > 0 ? process.argv[i + 1] : vars; };
const hedef = arg("hedef", "once");
const cikti = path.join(KOK, arg("cikti", "baseline"));
const motorlar = arg("motor", "chromium,firefox,webkit").split(",");
const sonuc = [];
for (const motor of motorlar) {
  const t = await motorAc(motor, hedef);
  for (const [gAd, g] of Object.entries(GORUNUMLER)) {
    const b = await t.newContext(baglamAyar(motor, g)); const s = await b.newPage();
    for (const [sAd, yol] of Object.entries(SAYFALAR)) {
      // ısıt + sıcak yükleme; aralarında about:blank (Playwright Firefox'ta aynı adrese doğrudan ikinci gezinme ara sıra «load»a ulaşmıyor —
      // düzenek bulgusu, stok Firefox'ta yeniden üretilemedi); takılırsa bir kez yeniden denenir
      for (let d = 0; d < 2; d++) {
        try { await s.goto(HEDEFLER[hedef].yok + yol, { waitUntil: "load", timeout: 45000 }); await s.goto("about:blank"); await s.goto(HEDEFLER[hedef].yok + yol, { waitUntil: "load", timeout: 45000 }); break; }
        catch (e) { if (d) throw e; await s.goto("about:blank").catch(() => {}); }
      }
      await s.waitForTimeout(2500);
      const r = await s.evaluate(() => {
        const ozellik = { backdrop: (c) => (c.backdropFilter || c.webkitBackdropFilter || "none") !== "none", filtre: (c) => c.filter && c.filter !== "none",
          karisim: (c) => c.mixBlendMode && c.mixBlendMode !== "normal", maske: (c) => (c.maskImage || c.webkitMaskImage || "none") !== "none" };
        const ilk = innerWidth * innerHeight, top = {};
        for (const k of Object.keys(ozellik)) top[k] = { adet: 0, alan: 0, ilkEkranAlan: 0, ornek: [] };
        for (const el of document.querySelectorAll("body *")) for (const sozde of [null, "::before", "::after"]) {
          const c = getComputedStyle(el, sozde); if (sozde && (c.content === "none" || c.content === "normal")) continue;
          const r = el.getBoundingClientRect(); if (r.width * r.height === 0 || c.display === "none" || c.visibility === "hidden") continue;
          const ad = el.tagName.toLowerCase() + (el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\s+/)[0] : "") + (sozde || "");
          for (const [k, f] of Object.entries(ozellik)) if (f(c)) {
            const t = top[k]; t.adet++; t.alan += r.width * r.height;
            const y0 = r.top + scrollY, kes = Math.max(0, Math.min(r.right, innerWidth) - Math.max(r.left, 0)) * Math.max(0, Math.min(y0 + r.height, innerHeight) - Math.max(y0, 0));
            t.ilkEkranAlan += kes; if (t.ornek.length < 12) t.ornek.push(`${ad} ${Math.round(r.width)}×${Math.round(r.height)} ${k === "backdrop" ? (c.backdropFilter || c.webkitBackdropFilter) : k === "filtre" ? c.filter : k === "karisim" ? c.mixBlendMode : "maske"}${c.position === "fixed" || c.position === "sticky" ? " [" + c.position + "]" : ""}`);
          }
        }
        for (const t of Object.values(top)) { t.ilkEkranOran = +(t.ilkEkranAlan / ilk).toFixed(3); t.alan = Math.round(t.alan); t.ilkEkranAlan = Math.round(t.ilkEkranAlan); }
        return top;
      });
      sonuc.push({ motor, surum: t.version(), gorunum: gAd, sayfa: sAd, ...r });
      console.log(motor, gAd, sAd, Object.entries(r).map(([k, v]) => `${k} ${v.adet} adet, ilk ekranın %${Math.round(100 * v.ilkEkranOran)}'i`).join(" · "));
    }
    await b.close();
  }
  await t.close();
}
fs.writeFileSync(path.join(cikti, "envanter.json"), JSON.stringify(sonuc, null, 1));
