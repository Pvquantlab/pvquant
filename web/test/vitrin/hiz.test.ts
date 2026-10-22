// 16.10 hız turu 4 — açılış sırası sözleşmeleri: satır içi kabuk betikleri, hero video kapısı, heroHazir sinyali,
// erken doğrulama, panel geçişleri, yayın sonrası yenileme ve CSS kuralları. Kaynak metni okunur (derleme gerekmez).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { hatYavasKayitli, hatiYenidenOlc, heroBekle, heroHazirMi, heroHazirOldu, heroHazirSoz, levhaKuyruguBasladi, levhalarBittiAbone, levhalarBittiOldu, levhalarBittiSoz, posterYavasMi, yavasKararKayittan } from "../../src/features/vitrin/heroHazir.ts";

const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");
const yapi = oku("../../vite.config.ts");

/** vite.config'teki üç satır içi betiğin JS gövdeleri (dize birleştirmeleri çözülerek). */
function betikler(): { bas: string; erken: string; govde: string } {
  const al = (ad: string) => {
    const m = new RegExp(`const ${ad} = ([\\s\\S]*?)\\n\\s*(?:if|let|const)\\b`).exec(yapi);
    assert.ok(m, `${ad} bulunamadı`);
    // '…' + `…${poster}…` + '…' dizilerini birleştir; poster adını sabitle
    const parcalar = [...m[1].matchAll(/'([^']*)'|`([^`]*)`/g)].map((p) => (p[1] ?? p[2]).replace("${poster}", "assets/santral-poster-AbC123.webp"));
    return parcalar.join("").replace(/^<script>/, "").replace(/<\/script>$/, "");
  };
  return { bas: al("bas"), erken: al("erken"), govde: al("betik") };
}

/** Betiği sahte tarayıcı ortamında çalıştırır; ne yaptığını döndürür. */
function calistir(kod: string, yol: string, arama: string, jeton: string | null) {
  const olay = { kokTemizlendi: false, sinif: [] as string[], onyukleme: [] as Record<string, string>[], istek: [] as string[] };
  const kok = { set textContent(_: string) { olay.kokTemizlendi = true; } };
  const ortam = {
    location: { pathname: yol, search: arama },
    localStorage: { getItem: (k: string) => (k === "pvq_token" ? jeton : null) },
    document: {
      getElementById: (id: string) => (id === "root" ? kok : null),
      documentElement: { classList: { add: (c: string) => olay.sinif.push(c) } },
      createElement: () => ({} as Record<string, string>),
      head: { appendChild: (l: Record<string, string>) => olay.onyukleme.push(l) },
    },
    fetch: (u: string) => { olay.istek.push(u); return Promise.resolve({ ok: true, json: () => Promise.resolve({ durum: "kapali" }) }); },
    window: {} as Record<string, unknown>,
  };
  vm.runInNewContext(kod, ortam);
  return olay;
}

test("kabuk betiği: vitrin dalında poster ön yüklemesi, diğer yollarda kabuk silinir; /yontem'e vt-sayfa", () => {
  const { govde } = betikler();
  // vitrin: oturumsuz kök, ya da ?vitrin (oturum olsa da)
  for (const [yol, arama, jeton] of [["/", "", null], ["/", "?vitrin", "j"], ["/", "?a=1&vitrin", "j"]] as const) {
    const o = calistir(govde, yol, arama, jeton);
    assert.equal(o.kokTemizlendi, false, `${yol}${arama}`);
    assert.equal(o.onyukleme.length, 1);
    const l = o.onyukleme[0];
    assert.equal(l.rel, "preload"); assert.equal(l.as, "image"); assert.equal(l.fetchPriority, "high");
    assert.equal(l.href, "/assets/santral-poster-AbC123.webp");
    assert.equal(l.crossOrigin, undefined, "crossorigin YOK — <img>/video posteri no-cors ister");
  }
  for (const [yol, arama, jeton, sinif] of [["/", "", "j", false], ["/yontem", "", null, true], ["/parola-yenile", "", null, false], ["/baska", "", null, false]] as const) {
    const o = calistir(govde, yol, arama, jeton);
    assert.equal(o.kokTemizlendi, true, `${yol}`);
    assert.equal(o.onyukleme.length, 0);
    assert.deepEqual(o.sinif, sinif ? ["vt-sayfa"] : []);
  }
  assert.match(oku("../../src/index.css"), /html\.vt-sayfa body \{ background: #FFFFFF; \}/);
});

test("baş betiği: kabuksuz yollarda kabuk ilk boyamadan önce gizlenir (yanlış rota karesi yok); vitrin dalına dokunmaz", () => {
  const { bas, govde } = betikler();
  const durumlar = [["/", "", null], ["/", "?vitrin", "j"], ["/", "?a=1&vitrin", "j"], ["/", "?vitrin=1", "j"], ["/", "?vitrinx", "j"], ["/", "", "j"],
    ["/yontem", "", null], ["/yontem", "", "j"], ["/yontem/", "", null], ["/parola-yenile", "", null], ["/baska", "", null]] as const;
  for (const [yol, arama, jeton] of durumlar) {
    const b = calistir(bas, yol, arama, jeton);
    const g = calistir(govde, yol, arama, jeton);
    // iki betik aynı kararı verir: gizlenen kabuk gövde betiğinde silinir; korunan kabuk hiç gizlenmez
    assert.equal(b.sinif.includes("vt-kabuksuz"), g.kokTemizlendi, `${yol}${arama} jeton=${jeton}`);
    assert.deepEqual(b.sinif, !g.kokTemizlendi ? [] : yol === "/yontem" ? ["vt-kabuksuz", "vt-sayfa"] : ["vt-kabuksuz"]);
    assert.equal(b.onyukleme.length + b.istek.length, 0, "baş betiği yalnız sınıf koyar");
  }
  assert.match(yapi, /const basStil = '<style>html\.vt-kabuksuz #root>\[data-kabuk\]\{display:none\}<\/style>'/);
  assert.ok(yapi.includes("`<meta charset=\"UTF-8\" />\\n    ${bas}\\n    ${basStil}`"), "baş betiği ve kuralı <head>'in başında, her derlemede");
  assert.ok(oku("../../src/features/vitrin/VitrinKabugu.tsx").includes('<div className="vt vt--a" data-kabuk="">'));
  for (const d of ["Vitrin.tsx", "Yontem.tsx"]) {
    assert.ok(!oku(`../../src/features/vitrin/${d}`).includes("data-kabuk"), `${d}: React ağacında data-kabuk olmamalı`);
  }
});

test("erken doğrulama: yalnız vitrin ve /yontem, aynı köken derlemesinde; useDogrulama aynı adları okur", () => {
  const { erken } = betikler();
  for (const [yol, arama, jeton, beklenen] of [["/", "", null, 1], ["/", "?vitrin", "j", 1], ["/yontem", "", "j", 1], ["/", "", "j", 0], ["/parola-yenile", "", null, 0]] as const) {
    assert.equal(calistir(erken, yol, arama, jeton).istek.length, beklenen, `${yol}${arama} jeton=${jeton}`);
  }
  assert.deepEqual(calistir(erken, "/", "", null).istek, ["/v1/dogrulama"]);
  assert.match(yapi, /configResolved\(c\) \{ ayniKoken = c\.env\.VITE_API_URL === '\.' \}/);
  assert.match(oku("../../src/api/client.ts"), /fetch\(`\$\{TABAN\}\/v1\/dogrulama`\)/);
  const hook = oku("../../src/features/vitrin/useDogrulama.ts");
  assert.match(hook, /window\.__pvqDogrSonuc/); assert.match(hook, /window\.__pvqDogr\b/);
  assert.match(hook, /let erkenKullanildi = false;/, "erken sonuç sayfa başına bir kez kullanılır");
  assert.match(oku("../../../Dockerfile.web"), /ARG VITE_API_URL=\./);
  const html = oku("../../index.html");
  assert.ok(html.includes('<meta charset="UTF-8" />') && html.includes('<div id="root"></div>'), "eklentinin bağlandığı işaretler");
});

test("hero videosu: load() yalnız hero ekrandayken bir kez, ayrılışta indirme kesilir", () => {
  const hero = oku("../../src/features/vitrin/Hero.tsx");
  assert.equal((hero.match(/v\.load\(\)/g) ?? []).length, 2);
  assert.match(hero, /if \(ekranda && !yuklendi\) \{ yuklendi = true; v\.preload = "auto"; v\.load\(\); v\.playbackRate = OYNATMA_HIZI; \}/);
  assert.match(hero, /if \(!v\.isConnected\) \{[^}]*v\.load\(\); \}/);
  assert.match(hero, /const basla = \(\) => \{ bekleme = window\.setTimeout\(ac, LEVHA_BEKLEME_MS\); birak = levhalarBittiAbone\(ac\); \};/, "load olayı yüklemeyi kendisi başlatmaz; levha kuyruğunu bekler");
  assert.match(hero, /const ac = \(\) => \{ if \(sokuldu \|\| izin\) return; window\.clearTimeout\(bekleme\); birak\(\); izin = true; uygula\(\); \};/);
  assert.match(hero, /sokuldu = true; window\.clearTimeout\(bekleme\); birak\(\);/, "sökümde levha dinleyicisi bırakılır");
  assert.match(hero, /const LEVHA_BEKLEME_MS = 4000;/);
});

test("heroHazir: bekleme ve hazır sinyali", async () => {
  // modül durumu dosya başına tek: önce hazır sayılır (bekleyen yok)
  assert.equal(heroHazirMi(), true);
  heroBekle();
  assert.equal(heroHazirMi(), false);
  let cozuldu = false;
  const soz = heroHazirSoz().then(() => { cozuldu = true; });
  await Promise.resolve();
  assert.equal(cozuldu, false);
  heroHazirOldu();
  await soz;
  assert.equal(cozuldu, true);
  heroBekle();                                  // hazırdan sonra etkisiz
  assert.equal(heroHazirMi(), true);
  const tl = oku("../../src/features/vitrin/TurkiyePiyasasi.tsx");
  assert.match(tl, /const \[capa\] = useState\(\(\) => window\.location\.hash === "#para"\);\n\s*if \(capa\) heroBekle\(\);/);
  assert.match(tl, /onLoad=\{capa \? heroHazirOldu : undefined\} onError=\{capa \? heroHazirOldu : undefined\}/);
  assert.match(tl, /window\.setTimeout\(heroHazirOldu, 5000\)/);
});

test("çapalı açılış: sınıflama kaydırmadan sonra; useCapaKaydir önce çağrılır", () => {
  const c = oku("../../src/features/vitrin/useCanlandir.ts");
  assert.match(c, /if \(window\.location\.hash\) kare = requestAnimationFrame\(siniflandir\); else siniflandir\(\);/);
  assert.match(c, /cancelAnimationFrame\(kare\)/);
  for (const d of ["Vitrin.tsx", "Yontem.tsx"]) {
    const k = oku(`../../src/features/vitrin/${d}`);
    const a = k.indexOf("useCapaKaydir(durum.tur)"), b = k.indexOf("useCanlandir(durum.tur)");
    assert.ok(a >= 0 && a < b, d);
  }
});

test("K1 levha önden indirmesi: yavaş hat kararını okur, ölçüm yapmaz", () => {
  const c = oku("../../src/features/vitrin/useCanlandir.ts");
  assert.match(c, /if \(yavas \|\| hatYavasKayitli\(\)\) \{ levhalarBittiOldu\(\); return; \}/);
  assert.doesNotMatch(c, /posterYavasMi/, "ölçüm ve kayıt yalnız Hero'da");
});

test("panel geçişleri: ekran değişimleri startTransition içinde, tek kalıcı Suspense + kabuk içi Suspense", () => {
  const app = oku("../../src/App.tsx");
  assert.match(app, /const sayfaSec = \(s: SayfaId\) => startTransition\(\(\) => setSayfa\(s\)\);/);
  assert.match(app, /setSayfa=\{sayfaSec\}/);
  assert.doesNotMatch(app.replace(/startTransition\(\(\) => [^;\n]*\);/g, ""), /[^.]set(Sayfa|Girdi)\((true|"[a-z]+")\)/, "geçiş dışı ekran değişimi");
  assert.match(app, /if \(kusak === oturumKusagi\.current\) startTransition\(\(\) => setGirdi\(true\)\);/, "bekleyen giriş araya giren 401'i ezmez");
  assert.match(app, /startTransition\(\(\) => setGorunum\("giris"\)\)/);
  assert.match(app, /startTransition\(\(\) => \{ setGirdi\(false\); setGorunum\("giris"\); setGirisNo\(\(n\) => n \+ 1\); \}\)/);
  assert.match(app, /<Giris key=\{girisNo\}/);
  assert.equal((app.match(/<Suspense fallback=\{null\}>/g) ?? []).length, 2);
  assert.match(app, /return <Suspense fallback=\{null\}>\{icerik\}<\/Suspense>;/);
  assert.match(app, /Promise\.all\(\[Kabuk\.onYukle\(\), Santralim\.onYukle\(\)\]\)/);
  // giriş ekranı font bekleme listesi: her örnek ASCII + gerekirse Türkçe harf içerir (latin yüzü de istensin)
  const ornek = new Map([...app.matchAll(/document\.fonts\.load\("([^"]+)", "([^"]+)"\)/g)].map((m) => [m[1], m[2]]));
  assert.equal(ornek.size, 5);
  for (const [f, s] of ornek) assert.match(s, /[A-Za-z]/, f);
  for (const f of ["500 64px 'Inter Tight'", "400 16px 'Inter Variable'", "400 12px 'IBM Plex Mono'"]) assert.match(ornek.get(f) ?? "", /[ğşİ]/, f);
  assert.ok(ornek.has("500 12px 'IBM Plex Mono'") && ornek.has("600 12px 'IBM Plex Mono'"));
  assert.match(oku("../../src/features/giris/Giris.tsx"), /if \(r === "ok"\) \{ onGiris\(\); return; \}/);
  assert.match(oku("../../src/features/sayfalar/Digerleri.tsx"), /if \(tahminlereGit\) \{ tahminlereGit\(\);/);
});

test("yayın sonrası parça hatası: bir kez yenile, döngü yok, hata sınırı uygulamayı sarar", () => {
  const m = oku("../../src/main.tsx");
  assert.match(m, /window\.addEventListener\('vite:preloadError', \(e\) => \{/);
  assert.match(m, /if \(sessionStorage\.getItem\(YENILE\)\) return\n\s*sessionStorage\.setItem\(YENILE, '1'\)/);
  assert.ok(m.indexOf("e.preventDefault()") > m.indexOf("sessionStorage.setItem(YENILE, '1')"), "bayrak yenilemeden önce yazılır");
  assert.match(m, /sessionStorage\.removeItem\(YENILE\) \} catch \{ \/\* depo yok \*\/ \} \}, 10000\)/);
  assert.match(m, /if \(yenileniyor\) return null/);
  assert.match(m, /<HataSiniri>\s*<App \/>\s*<\/HataSiniri>/);
});

test("kabuktan devir: kabuk varken React ilk içerikli boyama bildirimini bekler; gizli sekme / API yok / 1 sn emniyet", () => {
  const m = oku("../../src/main.tsx");
  assert.match(m, /if \(!kok\.firstElementChild \|\| document\.visibilityState !== 'visible' \|\| window\.location\.hash\) return false/, "çapalı açılış beklemez");
  assert.match(m, /if \(performance\.getEntriesByName\('first-contentful-paint', 'paint'\)\.length > 0\) return false/, "bildirim zaten varsa beklenmez");
  assert.match(m, /g\.observe\(\{ type: 'paint', buffered: true \}\)/);
  assert.match(m, /getEntriesByName\('first-contentful-paint'\)\.length === 0\) return\n\s*g\.disconnect\(\)\n\s*baslat\(\)/, "geri çağrıda ek zamanlayıcı yok; render() zaten zamanlar");
  assert.match(m, /window\.setTimeout\(\(\) => \{ g\.disconnect\(\); baslat\(\) \}, 1000\)/);
  assert.doesNotMatch(m, /requestAnimationFrame/, "rAF gizli sekmede çalışmaz, sunumdan önce döner");
});

test("hero CSS: poster sahneyi örter, svh, kabuk dolgusu yalnız ince işaretçide", () => {
  const css = oku("../../src/features/vitrin/vitrin.css");
  assert.match(css, /\.vt \.vt-hero--video \.vt-hero__sahne \.vt-hero__poster \{ top: 0; right: 0; bottom: 0; left: 0; width: 100%; height: 100%; max-width: none; \}/);
  assert.doesNotMatch(css, /100dvh/, "hero yüksekliği adres çubuğuyla değişmesin (svh)");
  assert.match(css, /@media \(pointer: fine\) \{\n\s*\.vt \.vt-kabuk-dolgu \{ height: 100vh; \}\n\}/);
  assert.ok(oku("../../src/features/vitrin/VitrinKabugu.tsx").includes('className="vt-kabuk-dolgu"'));
  assert.ok(!oku("../../src/features/vitrin/Vitrin.tsx").includes("vt-kabuk-dolgu"), "dolgu yalnız kabukta");
  // «Hangi iş için» beyaz tepsisi kenar boşluklu: genişlik = kap − iki kenar boşluğu (%100 + kenar boşluğu kartı taşırıyordu, v2.454).
  // 18.10: «auto» yerine açık calc — WebKit gerilen öğede aspect-ratio'yu kenar boşluksuz genişlikten hesaplıyordu (kart 19 px uzun).
  assert.match(css, /\.vt #isler \.vt-is \.vt-levha--resim \{[^}]*margin: 12px 12px 0;[^}]*width: calc\(100% - 24px\); \}/);
  assert.match(css, /\.vt-levha--resim \{ position: relative; aspect-ratio: 10 \/ 8;/);
});

// 16.10 kullanıcı kararları: yavaş hatta video yok, melez döngü başlangıcı, tek parça açılış, HTTP/3
test("kararlar: yavaş hatta video inmez; ilk oynatma poster karesinden, döngü anahtar kareden", () => {
  const hero = oku("../../src/features/vitrin/Hero.tsx");
  const hh = oku("../../src/features/vitrin/heroHazir.ts");
  assert.match(hh, /const YAVAS_POSTER_MS = 2000;/);
  assert.match(hh, /const YAVAS_OMUR_MS = 7 \* 24 \* 3600 \* 1000;/);
  assert.match(hh, /if \(e\) return kaydet\(e\.responseEnd - e\.startTime > YAVAS_POSTER_MS\);/, "kararı yalnız ağ ölçümü yazar");
  assert.match(hero, /yavasHat\.current = posterYavasMi\(new URL\(santralPoster, window\.location\.href\)\.href\);/);
  assert.match(oku("../../src/features/sayfalar/Digerleri.tsx"), /tahminlereGit\(\); startTransition\(\(\) => setKosuyor\(false\)\); return;/);
  assert.match(hero, /if \(kisit \|\| mq\.matches\) return;/);
  // 21.10: kayıttan gelen «yavaş» karar yeniden ölçülür (günde bir); ağ ölçümünden gelen karar kesindir
  assert.match(hero, /if \(!yavasHat\.current\) sok = videoKur\(v\);\n\s*else if \(yavasKararKayittan\(\)\) \{\n\s*hatiYenidenOlc\(new URL\(santralPoster, window\.location\.href\)\.href\)\.then\(\(yavas\) => \{ if \(!birakildi && !yavas\) sok = videoKur\(v\); \}\);/);
  assert.match(hh, /const YAVAS_YENIDEN_MS = 24 \* 3600 \* 1000;/);
  assert.match(hh, /fetch\(adres, \{ cache: "reload", credentials: "omit" \}\)/, "yeniden ölçüm önbelleği atlar");
  assert.match(hero, /const ILK_BAS = 6\.0727;\nconst DONGU_BAS = 9\.009;\nconst DONGU_SON = 19\.0;/);
  assert.match(hero, /const basaSar = \(\) => \{ if \(!araliksiz\(\)\) v\.currentTime = ILK_BAS; \};/);
  assert.match(hero, /if \(t >= DONGU_SON\) \{ ilkTur = false; v\.currentTime = DONGU_BAS; return; \}/);
});

// 18.10 K1 motor bağımsız (kök neden H13). Girdi biçimleri perf/baseline/matris.jsonl'deki ölçülmüş değerlerden.
test("K1: kararı yalnız gövdesi aktarılmış ağ ölçümü yazar; önbellek biçimleri kaydı yalnız okur", () => {
  const depo = new Map<string, string>();
  let girdiler: object[] = [];
  const once = { ls: Object.getOwnPropertyDescriptor(globalThis, "localStorage"), pf: Object.getOwnPropertyDescriptor(globalThis, "performance") };
  Object.defineProperty(globalThis, "localStorage", { configurable: true, writable: true,
    value: { getItem: (k: string) => depo.get(k) ?? null, setItem: (k: string, v: string) => { depo.set(k, v); } } });
  Object.defineProperty(globalThis, "performance", { configurable: true, writable: true, value: { getEntriesByName: () => girdiler } });
  const A = "https://pvquant.com/assets/santral-poster-AbC123.webp";
  const kayit = () => depo.get("pvq_yavas_hat");
  const ag = (ms: number) => ({ startTime: 900, responseEnd: 900 + ms, transferSize: 485432, encodedBodySize: 485132, decodedBodySize: 485132 });
  try {
    assert.equal(posterYavasMi(A), false, "ilk ziyaret, girdi ve kayıt yok → video serbest");
    assert.equal(kayit(), undefined, "girdisiz yükleme yazmaz");
    assert.equal(yavasKararKayittan(), true, "ölçüm yok → karar kayıttan (boş)");
    girdiler = [ag(3400)];                                       // soğuk 3G: ağdan 3,4 sn
    assert.equal(posterYavasMi(A), true);
    assert.equal(yavasKararKayittan(), false, "ağ ölçümü → karar kesin, yeniden ölçülmez");
    const yavasKaydi = kayit();
    assert.equal(JSON.parse(yavasKaydi ?? "{}").y, true);
    const onbellek: [string, object[]][] = [
      ["Firefox bellek önbelleği: girdi yok", []],
      ["WebKit bellek önbelleği: 0/0/0", [{ startTime: 40, responseEnd: 40.4, transferSize: 0, encodedBodySize: 0, decodedBodySize: 0 }]],
      ["Chromium bellek/disk: aktarım 0", [{ startTime: 40, responseEnd: 46, transferSize: 0, encodedBodySize: 485132, decodedBodySize: 485132 }]],
      ["304: yalnız başlık", [{ startTime: 40, responseEnd: 640, transferSize: 300, encodedBodySize: 485132, decodedBodySize: 485132 }]],
      ["eski Safari, bayt alanı yok, hızlı", [{ startTime: 40, responseEnd: 60 }]],
    ];
    for (const [ad, g] of onbellek) {
      girdiler = g;
      assert.equal(posterYavasMi(A), true, ad + ": kayıtlı «yavaş» okunur");
      assert.equal(yavasKararKayittan(), true, ad + ": karar kayıttan → Hero yeniden ölçer");
      assert.equal(kayit(), yavasKaydi, ad + ": kayıt ezilmez");
    }
    girdiler = [{ startTime: 40, responseEnd: 40.4, transferSize: 0, encodedBodySize: 0, decodedBodySize: 0 }, ag(400)];
    assert.equal(posterYavasMi(A), false, "birden çok girdide ağ ölçümü seçilir");
    assert.equal(JSON.parse(kayit() ?? "{}").y, false);
    girdiler = [];
    assert.equal(posterYavasMi(A), false, "hızlı karar önbellekte de geçerli");
    girdiler = [{ startTime: 40, responseEnd: 2600 }];
    assert.equal(posterYavasMi(A), true, "eski Safari: 2 sn'yi aşan sonuç ağdır (önbellek 2 sn sürmez)");
    depo.set("pvq_yavas_hat", JSON.stringify({ y: true, t: Date.now() - 8 * 24 * 3600 * 1000 }));
    girdiler = [];
    assert.equal(hatYavasKayitli(), false, "7 günden eski karar düşer");
    assert.equal(posterYavasMi(A), false);
  } finally {
    for (const [ad, d] of [["localStorage", once.ls], ["performance", once.pf]] as const) {
      if (d) Object.defineProperty(globalThis, ad, d); else delete (globalThis as Record<string, unknown>)[ad];
    }
  }
});

// 21.10 canlı bulgu: kayıttan okunan «yavaş» karar posteri önbelleksiz yeniden indirerek sınanır (günde bir).
test("K1 yeniden ölçüm: yanlış «yavaş» kaydı ilk ziyarette düzelir; gerçek yavaş hat 24 saat tekrar indirmez; ağ hatası kaydı bozmaz", async () => {
  const depo = new Map<string, string>();
  let simdi = 0, indirme = 0, sureMs = 0, hata = false;
  const once = { ls: Object.getOwnPropertyDescriptor(globalThis, "localStorage"), pf: Object.getOwnPropertyDescriptor(globalThis, "performance"), f: Object.getOwnPropertyDescriptor(globalThis, "fetch") };
  Object.defineProperty(globalThis, "localStorage", { configurable: true, writable: true,
    value: { getItem: (k: string) => depo.get(k) ?? null, setItem: (k: string, v: string) => { depo.set(k, v); } } });
  Object.defineProperty(globalThis, "performance", { configurable: true, writable: true, value: { now: () => simdi, getEntriesByName: () => [] } });
  Object.defineProperty(globalThis, "fetch", { configurable: true, writable: true,
    value: async (_a: string, o: RequestInit) => { indirme++; assert.equal(o.cache, "reload"); if (hata) throw new Error("ağ yok"); simdi += sureMs; return { ok: true, arrayBuffer: async () => new ArrayBuffer(8) }; } });
  const A = "https://pvquant.com/assets/santral-poster-AbC123.webp";
  const kayit = () => JSON.parse(depo.get("pvq_yavas_hat") ?? "null") as { y?: boolean; t?: number; p?: number } | null;
  try {
    depo.set("pvq_yavas_hat", JSON.stringify({ y: true, t: Date.now() }));   // DevTools kısıtlamasında yazılmış yanlış karar
    sureMs = 900;
    assert.equal(await hatiYenidenOlc(A), false, "hızlı hat: karar düzelir");
    assert.equal(indirme, 1);
    assert.equal(kayit()?.y, false); assert.equal(typeof kayit()?.p, "number");
    depo.set("pvq_yavas_hat", JSON.stringify({ y: true, t: Date.now() }));
    sureMs = 3100;
    assert.equal(await hatiYenidenOlc(A), true, "gerçek yavaş hat: karar kalır");
    assert.equal(kayit()?.y, true);
    const p = kayit()?.p; assert.equal(typeof p, "number");
    assert.equal(await hatiYenidenOlc(A), true, "24 saat dolmadan yeniden indirilmez");
    assert.equal(indirme, 2);
    depo.set("pvq_yavas_hat", JSON.stringify({ y: true, t: Date.now(), p: Date.now() - 25 * 3600 * 1000 }));
    sureMs = 500;
    assert.equal(await hatiYenidenOlc(A), false, "24 saat geçince yeniden ölçülür");
    assert.equal(indirme, 3);
    depo.set("pvq_yavas_hat", JSON.stringify({ y: true, t: 123 }));
    hata = true;
    assert.equal(await hatiYenidenOlc(A), true, "ağ hatası: yavaş sayılır");
    assert.deepEqual(kayit(), { y: true, t: 123 }, "ağ hatasında kayıt değişmez");
  } finally {
    for (const [ad, d] of [["localStorage", once.ls], ["performance", once.pf], ["fetch", once.f]] as const) {
      if (d) Object.defineProperty(globalThis, ad, d); else delete (globalThis as Record<string, unknown>)[ad];
    }
  }
});

test("kararlar: bölümler tek parça açılır (kart kademesi yok, zemin solmaz)", () => {
  const css = oku("../../src/features/vitrin/vitrin.css");
  assert.doesNotMatch(css, /vt-canlan/, "kademe animasyonu geri gelmemeli");
  assert.doesNotMatch(css, /\[data-canlan\]\.is-bekliyor \{/, "bekleme tonu bölüme (zemine) uygulanmaz");
  assert.match(css, /\.vt \[data-canlan\]\.is-bekliyor > \* \{ opacity: \.85; transform: translateY\(10px\); \}/);
});

test("kararlar: HTTP/3 için UDP 443 yayınlanır", () => {
  assert.match(oku("../../../docker-compose.yml"), /- "443:443\/udp"/);
});

// 18.10 perf/cross-browser — poster ön yüklemesi ilk içerikli boyamanın bildiriminden sonra (metin LCP'siyle yarışmaz).
test("kabuk betiği: poster ön yüklemesi FCP bildirimini bekler; bildirim varsa / API yoksa hemen; 1 sn emniyet", () => {
  const { govde } = betikler();
  const kos = (fcpVar: boolean, destek: boolean) => {
    const eklenen: Record<string, string>[] = []; const zaman: (() => void)[] = []; let gozlemci: ((s: unknown) => void) | null = null;
    class PO { static supportedEntryTypes = destek ? ["paint", "largest-contentful-paint"] : ["navigation"];
      constructor(f: (s: unknown) => void) { gozlemci = f; } observe() {} disconnect() {} }
    vm.runInNewContext(govde, {
      location: { pathname: "/", search: "" }, localStorage: { getItem: () => null },
      document: { getElementById: () => null, documentElement: { classList: { add() {} } }, createElement: () => ({}), head: { appendChild: (l: Record<string, string>) => eklenen.push(l) }, querySelector: () => null },
      window: { PerformanceObserver: PO }, performance: { getEntriesByName: () => (fcpVar ? [{}] : []) },
      setTimeout: (f: () => void) => { zaman.push(f); return 1; },
    });
    return { eklenen, zaman, bildir: () => gozlemci?.({ getEntriesByName: (ad: string) => (ad === "first-contentful-paint" ? [{}] : []) }) };
  };
  const bekleyen = kos(false, true);
  assert.equal(bekleyen.eklenen.length, 0, "FCP bildirilmeden poster istenmez");
  bekleyen.bildir();
  assert.equal(bekleyen.eklenen.length, 1, "bildirimle hemen");
  bekleyen.zaman.forEach((f) => f());
  assert.equal(bekleyen.eklenen.length, 1, "emniyet zamanlayıcısı ikinci istek açmaz");
  assert.equal(kos(true, true).eklenen.length, 1, "FCP zaten varsa hemen");
  assert.equal(kos(false, false).eklenen.length, 1, "paint desteği yoksa hemen");
  const gizli = kos(false, true);
  gizli.zaman.forEach((f) => f());
  assert.equal(gizli.eklenen.length, 1, "bildirim gelmezse (gizli sekme) 1 sn sonra");
  assert.equal(gizli.eklenen[0].fetchPriority, "high");
});

// 18.10 perf/cross-browser — video ile levha önden indirmesi bandı paylaşmaz (20 Mbps'te Firefox kartları 1,7 → 5,2 sn).
test("levha kuyruğu sinyali: video levhalar bitince (ya da zaman aşımında) iner; kuyruk yoksa sinyal hemen", async () => {
  levhaKuyruguBasladi();
  let bitti = false;
  const soz = levhalarBittiSoz().then(() => { bitti = true; });
  await Promise.resolve();
  assert.equal(bitti, false);
  levhalarBittiOldu();
  await soz;
  assert.equal(bitti, true);
  levhaKuyruguBasladi();                                   // SPA: yeni sayfa = yeni kuyruk, eski «bitti» taşınmaz
  let ikinci = false;
  const soz2 = levhalarBittiSoz().then(() => { ikinci = true; });
  await Promise.resolve();
  assert.equal(ikinci, false);
  levhalarBittiOldu();
  await soz2;
  assert.equal(ikinci, true);
  levhaKuyruguBasladi();                                   // abonelik bırakılınca çağrılmaz; sinyal verilmişse hemen çağrılır
  let say = 0; const birak = levhalarBittiAbone(() => { say++; }); birak(); levhalarBittiOldu();
  assert.equal(say, 0, "bırakılan dinleyici çağrılmaz");
  levhalarBittiAbone(() => { say++; });
  assert.equal(say, 1, "sinyal zaten verildiyse hemen");
  const c = oku("../../src/features/vitrin/useCanlandir.ts");
  assert.match(c, /levhaKuyruguBasladi\(\);\n\s*if \(typeof IntersectionObserver === "undefined"\) \{ levhalarBittiOldu\(\); return; \}/);
  assert.match(c, /if \(hedefler\.length === 0\) \{ levhalarBittiOldu\(\); return; \}/);
  assert.match(c, /if \(yavas \|\| hatYavasKayitli\(\)\) \{ levhalarBittiOldu\(\); return; \}/);
  assert.match(c, /if \(i >= sira\.length\) \{ if \(--acik === 0\) levhalarBittiOldu\(\); return; \}/);
});
