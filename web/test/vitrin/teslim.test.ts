// 19.10 perf/cross-browser — HTML teslim sırası: font ön yüklemeleri <body> başında (Chromium <head>'dekileri ilk boyamayı
// engelleyen kaynak sayıyor), giriş CSS'i HTML'e gömülü, modül betiği stilin ardında. Eklentiler doğrudan çalıştırılır.
import { test } from "node:test";
import assert from "node:assert/strict";
import { cssGom, fontOnYukle } from "../../vite.config.ts";

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

test("giriş CSS'i HTML'e gömülür, modül betiği stilin ardında; göreli url() ve CSS'e başvuran demet derlemeyi durdurur", () => {
  const css = ".a{background:url(/assets/x-AbC123xy.webp)}.b{filter:url(#vt-keskin)}" +
    ".c{background:url(\"data:image/svg+xml,%3Csvg fill='url(%23d)'%3E\")}.d::after{content:\"$& $' $1\"}";
  const demet = (ek: Record<string, unknown> = {}) => ({
    "assets/index-DeF456zw.css": { type: "asset", source: css },
    "assets/index-AbC123xy.js": { type: "chunk", code: "console.log(1)" }, ...ek,
  });
  const p = cssGom();
  assert.equal((p as { apply?: string }).apply, "build", "geliştirme sunucusunda çalışmaz");
  const cikti = kanca(p).handler(HTML, { bundle: demet() });
  assert.doesNotMatch(cikti, /rel="stylesheet"/);
  const stil = cikti.indexOf(`    <style>${css}</style>\n`);
  const betik = cikti.indexOf('    <script type="module" crossorigin src="/assets/index-AbC123xy.js"></script>\n');
  assert.ok(stil > 0, "CSS olduğu gibi gömülü («$&» gibi diziler değiştirme deseni sayılmaz)");
  assert.ok(betik > stil, "modül betiği stilden sonra");
  assert.equal(cikti.match(/<script type="module"/g)?.length, 1);
  assert.ok(cikti.indexOf("</head>") > betik);
  // ikili kaynak (Uint8Array) da metin olarak gömülür
  const ikili = kanca(p).handler(HTML, { bundle: demet({ "assets/index-DeF456zw.css": { type: "asset", source: new TextEncoder().encode(".e{color:red}") } }) });
  assert.ok(ikili.includes("<style>.e{color:red}</style>"));
  // bozulma durumları derlemeyi durdurur
  assert.throws(() => kanca(p).handler(HTML, { bundle: demet({ "assets/index-DeF456zw.css": { type: "asset", source: ".a{background:url(resim.png)}" } }) }), /göreli url/);
  assert.throws(() => kanca(p).handler(HTML, { bundle: demet({ "assets/parca-x.js": { type: "chunk", code: 'f(["assets/index-DeF456zw.css"])' } }) }), /iki kez/);
  assert.throws(() => kanca(p).handler(HTML, { bundle: demet({ "assets/index-DeF456zw.css": { type: "asset", source: "a{}</style><p>" } }) }), /gömülemez/);
  assert.throws(() => kanca(p).handler(HTML.replace(/ *<link rel="stylesheet"[^>]*>\n/, ""), { bundle: demet() }), /bulunamadı/);
  assert.throws(() => kanca(p).handler(HTML, { bundle: {} }), /bulunamadı/);
});
