// deney-css.mjs — CSS'i HTML'e gömme deneyi (derlemesiz): <link rel=stylesheet> yerine <style>; modül betiği stilin ardına alınır.
// node olc/iz/deney-css.mjs <kaynak-ad> <hedef-ad>
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
const link = /^(\s*)<link rel="stylesheet" crossorigin href="\/(assets\/index-[\w-]+\.css)">\n/m.exec(html);
const betik = /^\s*<script type="module" crossorigin src="\/assets\/index-[\w-]+\.js"><\/script>\n/m.exec(html);
if (!link || !betik) throw new Error("link/betik yok");
const css = fs.readFileSync(path.join(R, hedef, "dist", link[2]), "utf8").replace(/<\/style/gi, "<\\/style");
html = html.replace(betik[0], "").replace(link[0], `${link[1]}<style>${css}</style>\n${betik[0]}`);
fs.writeFileSync(yol, html);
fs.writeFileSync(yol + ".br", brotliCompressSync(Buffer.from(html), { params: { [constants.BROTLI_PARAM_QUALITY]: 11 } }));
fs.writeFileSync(yol + ".gz", gzipSync(Buffer.from(html), { level: 9 }));
fs.writeFileSync(path.join(R, hedef, "REF"), `${fs.readFileSync(path.join(R, kaynak, "REF"), "utf8").trim()} + deney-css\n`);
console.log(hedef, "tamam; html", html.length, "B, br", fs.statSync(yol + ".br").size, "B");
