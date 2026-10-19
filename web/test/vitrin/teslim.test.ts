// 19.10 perf/cross-browser — HTML teslim sırası: font ön yüklemeleri <body> başında (Chromium <head>'dekileri ilk boyamayı
// engelleyen kaynak sayıyor), giriş CSS'i HTML'e gömülü, modül betiği stilin ardında. Eklentiler doğrudan çalıştırılır.
import { test } from "node:test";
import assert from "node:assert/strict";
import vm from "node:vm";
import { cssGom, fontBekle, fontOnYukle } from "../../vite.config.ts";

const HTML = `<!doctype html>
<html lang="tr">
  <head>
    <meta charset="UTF-8" />
    <script>(function(){try{if(!(location.pathname==="/")){var h=document.documentElement.classList;h.add("vt-kabuksuz")}}catch(e){}})()</script>
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
  const stil = cikti.indexOf(`<style>${css}</style>\n`);
  const betik = cikti.indexOf('    <script type="module" crossorigin src="/assets/index-AbC123xy.js"></script>\n');
  assert.ok(stil > 0, "CSS olduğu gibi gömülü («$&» gibi diziler değiştirme deseni sayılmaz)");
  assert.ok(betik > stil, "modül betiği stilden sonra");
  assert.equal(cikti.match(/<script type="module"/g)?.length, 1);
  assert.ok(cikti.indexOf("</head>") > betik);
  // kabuksuz yollarda (JS'le çizilen /yontem, panel) JS stil baytlarından ÖNCE istenir; vitrin dalında istenmez
  const erken = /<script>(try\{if\(document\.documentElement\.classList\.contains\("vt-kabuksuz"\)\)[\s\S]*?)<\/script>\n    <style>/.exec(cikti);
  assert.ok(erken && erken.index < stil, "erken JS betiği stilden hemen önce");
  for (const [kabuksuz, beklenen] of [[true, 1], [false, 0]] as const) {
    const eklenen: Record<string, string>[] = [];
    vm.runInNewContext(erken[1], { document: { documentElement: { classList: { contains: (c: string) => kabuksuz && c === "vt-kabuksuz" } },
      createElement: () => ({}), head: { appendChild: (l: Record<string, string>) => eklenen.push(l) } } });
    assert.equal(eklenen.length, beklenen);
    if (beklenen) assert.deepEqual({ ...eklenen[0] }, { rel: "modulepreload", crossOrigin: "anonymous", href: "/assets/index-AbC123xy.js" }, "modül betiğiyle aynı adres ve kimlik kipi");
  }
  // ikili kaynak (Uint8Array) da metin olarak gömülür
  const ikili = kanca(p).handler(HTML, { bundle: demet({ "assets/index-DeF456zw.css": { type: "asset", source: new TextEncoder().encode(".e{color:red}") } }) });
  assert.ok(ikili.includes("<style>.e{color:red}</style>"));
  // bozulma durumları derlemeyi durdurur
  assert.throws(() => kanca(p).handler(HTML, { bundle: demet({ "assets/index-DeF456zw.css": { type: "asset", source: ".a{background:url(resim.png)}" } }) }), /göreli url/);
  assert.throws(() => kanca(p).handler(HTML, { bundle: demet({ "assets/parca-x.js": { type: "chunk", code: 'f(["assets/index-DeF456zw.css"])' } }) }), /iki kez/);
  assert.throws(() => kanca(p).handler(HTML, { bundle: demet({ "assets/index-DeF456zw.css": { type: "asset", source: "a{}</style><p>" } }) }), /gömülemez/);
  assert.throws(() => kanca(p).handler(HTML.replace(/ *<link rel="stylesheet"[^>]*>\n/, ""), { bundle: demet() }), /bulunamadı/);
  assert.throws(() => kanca(p).handler(HTML, { bundle: {} }), /bulunamadı/);
  assert.throws(() => kanca(p).handler(HTML.replace(/ *<script>\(function\(\)\{try\{if\(!\(location[^\n]*\n/, ""), { bundle: demet() }), /vt-kabuksuz/, "kabuk baş betiği yoksa derleme durur");
});

test("vitrinde ilk kare web fontunu en çok 100 ms bekler — yalnız Chromium/Gecko, yalnız vitrin dalı; gömülü CSS'ten sonra", () => {
  const p = fontBekle();
  assert.equal((p as { apply?: string }).apply, "build");
  const gomulu = HTML.replace(/ *<link rel="stylesheet"[^>]*>\n/, "    <style>@font-face{font-family:Inter Tight;font-display:swap;src:url(/assets/x.woff2)}</style>\n");
  const cikti = kanca(p).handler(gomulu, {});
  const [bas] = cikti.split("</head>");
  assert.ok(bas.indexOf("html.vt-font-bekle #root{visibility:hidden}") > bas.indexOf("font-family:Inter Tight"), "kural gömülü CSS'ten sonra");
  const betik = /<script>(\(function\(\)\{try\{var h=document\.documentElement,f=document\.fonts;[\s\S]*?)<\/script>\n {2}<\/head>/.exec(cikti);
  assert.ok(betik, "betik </head>'den hemen önce");
  const calistir = (ua: string, kabuksuz: boolean, fontlarVar = true) => {
    const sinif = new Set<string>(kabuksuz ? ["vt-kabuksuz"] : []), zaman: (() => void)[] = [], yukleme: string[] = [];
    let coz: () => void = () => {};
    const fonts = fontlarVar ? { load: (f: string, m: string) => { yukleme.push(`${f}|${m}`); return new Promise<void>((r) => { coz = r; }); } } : undefined;
    vm.runInNewContext(betik![1], { navigator: { userAgent: ua }, setTimeout: (f: () => void) => zaman.push(f), Promise,
      document: { fonts, documentElement: { classList: { contains: (c: string) => sinif.has(c), add: (c: string) => sinif.add(c), remove: (c: string) => sinif.delete(c) } } } });
    return { sinif, zaman, yukleme, coz: () => coz() };
  };
  const CHROME = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36";
  const FIREFOX = "Mozilla/5.0 (X11; Linux x86_64; rv:158.0) Gecko/20100101 Firefox/158.0";
  const SAFARI = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Safari/605.1.15";
  const IOS_CHROME = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/140.0 Mobile/15E148 Safari/604.1";
  for (const ua of [CHROME, FIREFOX]) {
    const o = calistir(ua, false);
    assert.ok(o.sinif.has("vt-font-bekle"), ua);
    assert.deepEqual(o.yukleme, ['600 1em "Inter Tight"|aĞğİıŞş', '500 1em "Inter Tight"|aĞğİıŞş'], "Türkçe alt küme dahil 500 ve 600");
    o.zaman[0]();
    assert.equal(o.sinif.has("vt-font-bekle"), false, "100 ms'de açılır");
  }
  for (const [ua, kabuksuz, fontlar] of [[SAFARI, false, true], [IOS_CHROME, false, true], [CHROME, true, true], [CHROME, false, false]] as const) {
    assert.equal(calistir(ua, kabuksuz, fontlar).sinif.has("vt-font-bekle"), false, `${ua.slice(-30)} kabuksuz=${kabuksuz} fonts=${fontlar}: bekleme yok`);
  }
  assert.throws(() => kanca(p).handler(HTML, {}), /gömülü Inter Tight/, "cssGom'dan önce çalışırsa derleme durur");
  assert.throws(() => kanca(p).handler(gomulu.replace(/ *<script>\(function\(\)\{try\{if\(!\(location[^\n]*\n/, ""), {}), /kabuk baş betiği/);
});

test("font bekleme: yazı tipi sözü çözülünce zamanlayıcıyı beklemeden açılır", async () => {
  const p = fontBekle();
  const gomulu = HTML.replace(/ *<link rel="stylesheet"[^>]*>\n/, "    <style>@font-face{font-family:Inter Tight;src:url(/x.woff2)}</style>\n");
  const betik = /<script>(\(function\(\)\{try\{var h=document\.documentElement,f=document\.fonts;[\s\S]*?)<\/script>/.exec(kanca(p).handler(gomulu, {}))![1];
  const sinif = new Set<string>(); const coz: (() => void)[] = [];
  vm.runInNewContext(betik, { navigator: { userAgent: "Firefox/158.0" }, setTimeout: () => 0, Promise,
    document: { fonts: { load: () => new Promise<void>((r) => coz.push(r)) }, documentElement: { classList: { contains: (c: string) => sinif.has(c), add: (c: string) => sinif.add(c), remove: (c: string) => sinif.delete(c) } } } });
  assert.equal(sinif.has("vt-font-bekle"), true);
  coz[0](); await Promise.resolve(); await Promise.resolve();
  assert.equal(sinif.has("vt-font-bekle"), true, "iki yüzden biri yüklenince açılmaz");
  coz[1](); await new Promise((r) => setImmediate(r));
  assert.equal(sinif.has("vt-font-bekle"), false, "500 ve 600 yüklenince açılır");
});

