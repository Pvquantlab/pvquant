// 19.10 perf/cross-browser — HTML teslim sırası: font ön yüklemeleri <body> başında (Chromium <head>'dekileri ilk boyamayı
// engelleyen kaynak sayıyor). Eklentiler doğrudan çalıştırılır.
import { test } from "node:test";
import assert from "node:assert/strict";
import { fontOnYukle } from "../../vite.config.ts";

const HTML = `<!doctype html>
<html lang="tr">
  <head>
    <meta charset="UTF-8" />
    <title>t</title>
    <script type="module" crossorigin src="/assets/index-AbC123xy.js"></script>
    <link rel="stylesheet" crossorigin href="/assets/index-DeF456zw.css">
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
`;
type Kanca = { handler: (html: string, ctx: unknown) => string };
const kanca = (p: { transformIndexHtml?: unknown }) => p.transformIndexHtml as Kanca;

test("font ön yüklemeleri <body> başında, <head>'de değil (Chromium ilk boyamayı bekletmesin)", () => {
  const p = fontOnYukle();
  (p.generateBundle as (o: unknown, b: Record<string, unknown>) => void)({}, {
    "assets/inter-tight-latin-500-normal-AbC123xy.woff2": {}, "assets/inter-tight-tr-600-AbC123xy.woff2": {},
    "assets/inter-tight-latin-400-normal-AbC123xy.woff2": {}, "assets/index-AbC123xy.js": {},
  });
  const cikti = kanca(p).handler(HTML, {});
  const [bas, govde] = cikti.split("<body>");
  assert.doesNotMatch(bas, /rel="preload"/);
  assert.ok(govde.startsWith(
    '\n    <link rel="preload" as="font" type="font/woff2" crossorigin href="/assets/inter-tight-latin-500-normal-AbC123xy.woff2" />' +
    '\n    <link rel="preload" as="font" type="font/woff2" crossorigin href="/assets/inter-tight-tr-600-AbC123xy.woff2" />' +
    '\n    <div id="root"></div>'), govde);
  assert.doesNotMatch(cikti, /latin-400/);
  // geliştirme sunucusu: demet yok → HTML'e dokunulmaz
  assert.equal(kanca(fontOnYukle()).handler(HTML, {}), HTML);
});
