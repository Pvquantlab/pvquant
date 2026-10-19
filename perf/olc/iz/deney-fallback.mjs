// deney-fallback.mjs — gömülü CSS'te YALNIZ Inter Tight @font-face'lerinde font-display: swap → fallback (derlemesiz deney).
// node olc/iz/deney-fallback.mjs <kaynak-ad> <hedef-ad>
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { brotliCompressSync, constants, gzipSync } from "node:zlib";
const [kaynak, hedef] = process.argv.slice(2);
const R = path.resolve(".replika");
fs.rmSync(path.join(R, hedef), { recursive: true, force: true }); fs.mkdirSync(path.join(R, hedef), { recursive: true });
execFileSync("cp", ["-R", path.join(R, kaynak, "dist"), path.join(R, hedef, "dist")]);
const yol = path.join(R, hedef, "dist", "index.html");
let html = fs.readFileSync(yol, "utf8"), n = 0;
html = html.replace(/@font-face\{[^}]*\}/g, (b) => (/font-family:\s*["']?Inter Tight["']?;/.test(b) && /font-display:\s*swap/.test(b) ? (n++, b.replace(/font-display:\s*swap/, "font-display:fallback")) : b));
fs.writeFileSync(yol, html);
fs.writeFileSync(yol + ".br", brotliCompressSync(Buffer.from(html), { params: { [constants.BROTLI_PARAM_QUALITY]: 11 } }));
fs.writeFileSync(yol + ".gz", gzipSync(Buffer.from(html), { level: 9 }));
fs.writeFileSync(path.join(R, hedef, "REF"), `${fs.readFileSync(path.join(R, kaynak, "REF"), "utf8").trim()} + deney-fallback (${n} yüz)\n`);
console.log(hedef, "tamam;", n, "Inter Tight yüzü fallback");
