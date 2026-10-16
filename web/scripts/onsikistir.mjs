// 16.10 hız turu 4 — derleme sonrası ön-sıkıştırma: dist'teki metin dosyalarının yanına .br (brotli 11) ve .gz (gzip 9)
// yazar; Caddyfile.web «file_server { precompressed br gzip }» bunları olduğu gibi gönderir. Ölçüm (v2.452 derlemesi):
// kritik yol metni (HTML+CSS+JS) canlıda anlık zstd ile 121 857 B, brotli 11 ile 97 887 B (−%19,7). Anlık sıkıştırma
// her istekte CPU harcıyor ve hız için düşük seviyede kalıyor; burada bir kez, en yüksek seviyede yapılır.
// Görsel/video/font zaten sıkışık — dokunulmaz (kullanıcı kuralı: dosyalar bayt bayt). Kullanım: node scripts/onsikistir.mjs dist
import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { brotliCompressSync, constants, gzipSync } from "node:zlib";

const kok = process.argv[2];
if (!kok) { console.error("kullanım: node scripts/onsikistir.mjs <dist>"); process.exit(1); }
const UZANTI = /\.(js|mjs|css|html|svg|json|txt|xml|webmanifest)$/i;
const ESIK = 1024;   // daha küçüğünde başlık yükü kazancı yer
let adet = 0, ham = 0, br = 0;
const gez = (dizin) => {
  for (const ad of readdirSync(dizin)) {
    const yol = join(dizin, ad);
    const st = statSync(yol);
    if (st.isDirectory()) { gez(yol); continue; }
    if (!UZANTI.test(ad) || st.size < ESIK) continue;
    const veri = readFileSync(yol);
    const b = brotliCompressSync(veri, { params: { [constants.BROTLI_PARAM_QUALITY]: 11, [constants.BROTLI_PARAM_SIZE_HINT]: veri.length } });
    const g = gzipSync(veri, { level: 9 });
    if (b.length < veri.length) writeFileSync(yol + ".br", b);
    if (g.length < veri.length) writeFileSync(yol + ".gz", g);
    adet++; ham += veri.length; br += Math.min(b.length, veri.length);
  }
};
gez(kok);
console.log(`ön-sıkıştırma: ${adet} dosya, ${(ham / 1024).toFixed(0)} KB → brotli ${(br / 1024).toFixed(0)} KB`);
