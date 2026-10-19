// deney-font.mjs — font ön yüklemesinin yeri deneyi (derlemesiz): bir replikanın dist'ini kopyalar, <head>'deki 4 font preload'ını
// G1: <body> başındaki betikle ekler · G2: <body> başına statik taşır. index.html.br/.gz yeniden üretilir.
// node olc/iz/deney-font.mjs <kaynak-ad> <hedef-ad> G1|G2
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { brotliCompressSync, constants, gzipSync } from "node:zlib";
const [kaynak, hedef, tur] = process.argv.slice(2);
const R = path.resolve(".replika");
fs.rmSync(path.join(R, hedef), { recursive: true, force: true });
fs.mkdirSync(path.join(R, hedef), { recursive: true });
execFileSync("cp", ["-R", path.join(R, kaynak, "dist"), path.join(R, hedef, "dist")]);
const yol = path.join(R, hedef, "dist", "index.html");
let html = fs.readFileSync(yol, "utf8");
const re = /^\s*<link rel="preload" as="font" type="font\/woff2" crossorigin href="([^"]+)" \/>\n/gm;
const adresler = [...html.matchAll(re)].map((m) => m[1]);
if (adresler.length !== 4) throw new Error("4 font preload bekleniyordu: " + adresler.length);
html = html.replace(re, "");
const ek = tur === "G1"
  ? `<script>(function(){try{${JSON.stringify(adresler)}.forEach(function(u){var l=document.createElement("link");l.rel="preload";l.as="font";l.type="font/woff2";l.crossOrigin="anonymous";l.href=u;document.head.appendChild(l)})}catch(e){}})()</script>`
  : adresler.map((u) => `<link rel="preload" as="font" type="font/woff2" crossorigin href="${u}" />`).join("\n    ");
if (!html.includes("<body>\n")) throw new Error("<body> yok");
html = html.replace("<body>\n", `<body>\n    ${ek}\n`);
fs.writeFileSync(yol, html);
fs.writeFileSync(yol + ".br", brotliCompressSync(Buffer.from(html), { params: { [constants.BROTLI_PARAM_QUALITY]: 11 } }));
fs.writeFileSync(yol + ".gz", gzipSync(Buffer.from(html), { level: 9 }));
fs.writeFileSync(path.join(R, hedef, "REF"), `${fs.readFileSync(path.join(R, kaynak, "REF"), "utf8").trim()} + deney-font ${tur}\n`);
console.log(hedef, tur, "tamam;", adresler.length, "font");
