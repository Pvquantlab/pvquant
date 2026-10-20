// webkit-video-onbellek.mjs — WebKit sıcak ziyarette videoyu neden yeniden indiriyor? Üç sunucu çeşidi (Caddy başlıkları aynen /
// Vary yok / Accept-Ranges yok), aynı bağlamda iki açılış, sunucu tarafında yön başına gönderilen bayt.
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { webkit, chromium, firefox } from "playwright";
const dosya = path.resolve("../web/src/features/vitrin/varlik/santral-1440.mp4"); const boy = fs.statSync(dosya).size;
const etag = '"sabit-etag-1"', lm = "Mon, 19 Oct 2026 19:45:10 GMT";
const CESIT = {
  caddy:      { vary: true,  range: true,  ck: "public, max-age=31536000, immutable" },
  varyYok:    { vary: false, range: true,  ck: "public, max-age=31536000, immutable" },
  rangeYok:   { vary: true,  range: false, ck: "public, max-age=31536000, immutable" },
  noStore:    { vary: true,  range: true,  ck: "no-store" },
};
const sunucular = {}; let port = 18700;
for (const [ad, c] of Object.entries(CESIT)) {
  const s = { bayt: 0, istek: [] };
  const srv = http.createServer((req, res) => {
    if (req.url === "/") { res.setHeader("Content-Type", "text/html"); res.end(`<!doctype html><video id=v muted autoplay loop playsinline preload="auto" src="/v.mp4" width=640></video>`); return; }
    if (req.url !== "/v.mp4") { res.statusCode = 404; res.end(); return; }
    const h = { "Content-Type": "video/mp4", "Cache-Control": c.ck, "ETag": etag, "Last-Modified": lm };
    if (c.vary) h["Vary"] = "Accept-Encoding"; if (c.range) h["Accept-Ranges"] = "bytes";
    if (req.headers["if-none-match"] === etag && !req.headers.range) { res.writeHead(304, h); res.end(); s.istek.push("304"); return; }
    const r = c.range && req.headers.range ? /bytes=(\d*)-(\d*)/.exec(req.headers.range) : null;
    let bas = 0, bit = boy - 1;
    if (r) { bas = r[1] ? +r[1] : 0; bit = r[2] ? +r[2] : boy - 1; h["Content-Range"] = `bytes ${bas}-${bit}/${boy}`; res.writeHead(206, { ...h, "Content-Length": bit - bas + 1 }); }
    else res.writeHead(200, { ...h, "Content-Length": boy });
    s.istek.push((r ? "206 " + bas + "-" + bit : "200") + (req.headers["if-none-match"] ? " INM" : ""));
    const akis = fs.createReadStream(dosya, { start: bas, end: bit }); akis.on("data", (p) => { s.bayt += p.length; }); akis.pipe(res);
  }).listen(port);
  s.port = port; s.srv = srv; sunucular[ad] = s; port++;
}
for (const [mAd, m] of (process.argv.includes("--yalniz-webkit") ? [["webkit", webkit]] : [["webkit", webkit], ["chromium", chromium], ["firefox", firefox]])) {
  const t = await m.launch();
  for (const [ad, s] of Object.entries(sunucular)) {
    const c = await t.newContext(); const p = await c.newPage(); const sonuc = [];
    for (const acilis of [1, 2]) {
      const b0 = s.bayt, i0 = s.istek.length;
      await p.goto(`http://127.0.0.1:${s.port}/`, { waitUntil: "load" });
      await p.waitForFunction(() => { const v = document.getElementById("v"); return v && v.readyState >= 4; }, null, { timeout: 60000 }).catch(() => {});
      await p.waitForTimeout(12000);   // 37 MB'ın tamamı insin
      sonuc.push(`açılış ${acilis}: ${((s.bayt - b0) / 1e6).toFixed(1)} MB, istekler [${s.istek.slice(i0).join("; ").slice(0, 120)}]`);
    }
    console.log(`${mAd} · ${ad}: ${sonuc.join(" | ")}`);
    await c.close();
  }
  await t.close();
}
for (const s of Object.values(sunucular)) s.srv.close();
