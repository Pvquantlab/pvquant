// deney-poster.mjs — poster ön yüklemesinin ertelenmesini yalnız dar ekranla (≤760 px) sınırlama deneyi (derlemesiz).
// node olc/iz/deney-poster.mjs <kaynak-ad> <hedef-ad>
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { brotliCompressSync, constants, gzipSync } from "node:zlib";
const [kaynak, hedef] = process.argv.slice(2);
const R = path.resolve(".replika");
fs.rmSync(path.join(R, hedef), { recursive: true, force: true });
fs.mkdirSync(path.join(R, hedef), { recursive: true });
execFileSync("cp", ["-R", path.join(R, kaynak, "dist"), path.join(R, hedef, "dist")]);
const yol = path.join(R, hedef, "dist", "index.html");
let html = fs.readFileSync(yol, "utf8");
const eski = 'try{var P=window.PerformanceObserver;if(!P||';
if (html.split(eski).length !== 2) throw new Error("koşul bulunamadı");
html = html.replace(eski, 'try{var P=window.PerformanceObserver;if(!matchMedia("(max-width: 760px)").matches||!P||');
fs.writeFileSync(yol, html);
fs.writeFileSync(yol + ".br", brotliCompressSync(Buffer.from(html), { params: { [constants.BROTLI_PARAM_QUALITY]: 11 } }));
fs.writeFileSync(yol + ".gz", gzipSync(Buffer.from(html), { level: 9 }));
fs.writeFileSync(path.join(R, hedef, "REF"), `${fs.readFileSync(path.join(R, kaynak, "REF"), "utf8").trim()} + deney-poster\n`);
console.log(hedef, "tamam");
