// 16.10 hız turu 4 — web imajındaki Caddy sözleşmesi (Caddyfile.web) ve ön-sıkıştırma.
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");

test("eksik /assets/* SPA'ya düşmez; 1 yıllık başlık yalnız var olan varlığa", () => {
  const c = oku("../../Caddyfile.web");
  const varlik = /handle \/assets\/\* \{([\s\S]*?)\n\t\}/.exec(c)?.[1] ?? "";
  assert.ok(varlik, "handle /assets/* bloğu olmalı");
  assert.doesNotMatch(varlik, /try_files/, "varlık bloğunda index.html'e düşüş olmamalı");
  assert.match(c, /@varlik \{\s*path \/assets\/\*\s*file\s*\}/, "immutable başlığı file eşleyicisine bağlı olmalı");
  assert.match(c, /header @varlik Cache-Control "public, max-age=31536000, immutable"/);
  assert.match(c, /handle \{[\s\S]*header Cache-Control "no-cache"[\s\S]*try_files \{path\} \/index\.html/);
  assert.equal((c.match(/precompressed br gzip/g) ?? []).length, 2);
  // üst düzeyde bir try_files, handle'lardan ÖNCE çalışıp eksik varlığı yine index.html'e çevirir: tek try_files, çıplak handle içinde
  const kod = c.split("\n").filter((l) => !l.trim().startsWith("#")).join("\n");   // yorumlar sayılmaz
  assert.equal((kod.match(/try_files/g) ?? []).length, 1, "tek try_files olmalı");
  const ciplak = /\n\thandle \{([\s\S]*?)\n\t\}/.exec(c)?.[1] ?? "";
  assert.match(ciplak, /try_files \{path\} \/index\.html/, "try_files yalnız çıplak handle bloğunda");
});

test("imaj derlemesi ön-sıkıştırma betiğini çalıştırır", () => {
  assert.match(oku("../../Dockerfile.web"), /npm run build && node scripts\/onsikistir\.mjs dist/);
  const betik = oku("../scripts/onsikistir.mjs");
  assert.match(betik, /BROTLI_PARAM_QUALITY\]: 11/);
  // görsel/video/font zaten sıkışık ve bayt bayt korunur — uzantı listesine girmez
  const uzanti = /const UZANTI = \/(.*)\/(i?);/.exec(betik);
  assert.ok(uzanti, "UZANTI bulunamadı");
  const re = new RegExp(uzanti[1], uzanti[2]);
  for (const ad of ["a.png", "b.webp", "c.jpg", "d.jpeg", "e.avif", "f.gif", "g.mp4", "h.webm", "i.woff2", "j.woff", "k.PNG"]) assert.ok(!re.test(ad), `sıkıştırılmamalı: ${ad}`);
  for (const ad of ["index-x.js", "index-x.css", "index.html", "icons.svg", "a.json"]) assert.ok(re.test(ad), `sıkıştırılmalı: ${ad}`);
});

// 19.10 (v2.460): /robots.txt gerçek dosya olmalı. Yokken try_files onu da index.html'e çeviriyordu (200 text/html) —
// Lighthouse «robots.txt is not valid — 38 errors», SEO her sayfada 91. Burada tarayıcının yaptığı okunur: yalnız bilinen
// yönergeler, kurallar bir user-agent grubunun içinde, «*» için en uzun eşleşen kural kazanır (eşitlikte Allow, RFC 9309).
// Site haritası yok; Sitemap satırı eklenirse gösterdiği dosya public/'te olmalı (yoksa o adres de index.html'e düşer).
test("robots.txt geçerli, kamu sayfaları taranabilir, Sitemap yalnız var olan dosyayı gösterir", () => {
  const satirlar = oku("../public/robots.txt").split(/\r?\n/).map((l) => l.replace(/#.*/, "").trim()).filter(Boolean);
  assert.ok(satirlar.length, "robots.txt boş");
  const kurallar: { izin: boolean; desen: string }[] = [];
  let ajanlar: string[] = [], kuralda = false;   // grup = ardışık user-agent satırları + ardından gelen kurallar
  for (const l of satirlar) {
    const m = /^(user-agent|allow|disallow|sitemap)\s*:\s*(.*)$/i.exec(l);
    assert.ok(m, `tanınmayan satır: ${l}`);
    const ad = m[1].toLowerCase(), deger = m[2];
    if (ad === "sitemap") {
      const yol = new URL(deger).pathname;   // göreli adres burada patlar — yönerge mutlak URL ister
      assert.ok(existsSync(new URL(`../public${yol}`, import.meta.url)), `site haritası public/'te yok: ${yol}`);
    } else if (ad === "user-agent") {
      if (kuralda) { ajanlar = []; kuralda = false; }
      ajanlar.push(deger.toLowerCase());
    } else {
      assert.ok(ajanlar.length, `user-agent'tan önce kural: ${l}`);
      kuralda = true;
      if (ajanlar.includes("*")) kurallar.push({ izin: ad === "allow", desen: deger });
    }
  }
  const eslesir = (desen: string, yol: string) =>
    new RegExp("^" + desen.replace(/[.+?^{}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*")).test(yol);
  const izinli = (yol: string) => {
    const en = kurallar.filter((k) => k.desen && eslesir(k.desen, yol))
      .sort((a, b) => b.desen.length - a.desen.length || Number(b.izin) - Number(a.izin))[0];
    return !en || en.izin;
  };
  for (const yol of ["/", "/yontem"]) assert.ok(izinli(yol), `kamu sayfası taramaya kapalı: ${yol}`);
});
