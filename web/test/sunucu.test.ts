// 16.10 hız turu 4 — web imajındaki Caddy sözleşmesi (Caddyfile.web) ve ön-sıkıştırma.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

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
