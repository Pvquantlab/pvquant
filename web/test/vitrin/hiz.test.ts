// 16.10 hız turu 4 — açılış sırası sözleşmeleri: satır içi kabuk betikleri, hero video kapısı, heroHazir sinyali,
// erken doğrulama, panel geçişleri, yayın sonrası yenileme ve CSS kuralları. Kaynak metni okunur (derleme gerekmez).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { heroBekle, heroHazirMi, heroHazirOldu, heroHazirSoz } from "../../src/features/vitrin/heroHazir.ts";

const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");
const yapi = oku("../../vite.config.ts");

/** vite.config'teki iki satır içi betiğin JS gövdeleri (dize birleştirmeleri çözülerek). */
function betikler(): { erken: string; govde: string } {
  const al = (ad: string) => {
    const m = new RegExp(`const ${ad} = ([\\s\\S]*?)\\n\\s*(?:if|let|const)\\b`).exec(yapi);
    assert.ok(m, `${ad} bulunamadı`);
    // '…' + `…${poster}…` + '…' dizilerini birleştir; poster adını sabitle
    const parcalar = [...m[1].matchAll(/'([^']*)'|`([^`]*)`/g)].map((p) => (p[1] ?? p[2]).replace("${poster}", "assets/santral-poster-AbC123.webp"));
    return parcalar.join("").replace(/^<script>/, "").replace(/<\/script>$/, "");
  };
  return { erken: al("erken"), govde: al("betik") };
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
  assert.match(hero, /const basla = \(\) => \{ izin = true; uygula\(\); \};/, "load olayı yüklemeyi kendisi başlatmaz");
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
  for (const f of ["700 64px 'Space Grotesk'", "400 16px 'Inter Variable'", "400 12px 'IBM Plex Mono'"]) assert.match(ornek.get(f) ?? "", /[ğşİ]/, f);
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

test("hero CSS: poster sahneyi örter, svh, kabuk dolgusu yalnız ince işaretçide", () => {
  const css = oku("../../src/features/vitrin/vitrin.css");
  assert.match(css, /\.vt \.vt-hero--video \.vt-hero__sahne \.vt-hero__poster \{ top: 0; right: 0; bottom: 0; left: 0; width: 100%; height: 100%; max-width: none; \}/);
  assert.doesNotMatch(css, /100dvh/, "hero yüksekliği adres çubuğuyla değişmesin (svh)");
  assert.match(css, /@media \(pointer: fine\) \{\n\s*\.vt \.vt-kabuk-dolgu \{ height: 100vh; \}\n\}/);
  assert.ok(oku("../../src/features/vitrin/VitrinKabugu.tsx").includes('className="vt-kabuk-dolgu"'));
  assert.ok(!oku("../../src/features/vitrin/Vitrin.tsx").includes("vt-kabuk-dolgu"), "dolgu yalnız kabukta");
});

// 16.10 kullanıcı kararları: yavaş hatta video yok, melez döngü başlangıcı, tek parça açılış, HTTP/3
test("kararlar: yavaş hatta video inmez; ilk oynatma poster karesinden, döngü anahtar kareden", () => {
  const hero = oku("../../src/features/vitrin/Hero.tsx");
  assert.match(hero, /const YAVAS_POSTER_MS = 2000;/);
  assert.match(hero, /e\.responseEnd - e\.startTime > YAVAS_POSTER_MS/);
  assert.match(hero, /if \(e\.transferSize === 0 && e\.decodedBodySize > 0\) \{/, "önbellekten gelen poster ölçüm sayılmaz");
  assert.match(hero, /yavasHat\.current = posterYavasMi\(\);/);
  assert.match(oku("../../src/features/sayfalar/Digerleri.tsx"), /tahminlereGit\(\); startTransition\(\(\) => setKosuyor\(false\)\); return;/);
  assert.match(hero, /if \(kisit \|\| yavasHat\.current \|\| mq\.matches\) return;/);
  assert.match(hero, /const ILK_BAS = 6\.0727;\nconst DONGU_BAS = 9\.009;\nconst DONGU_SON = 19\.0;/);
  assert.match(hero, /const basaSar = \(\) => \{ if \(!araliksiz\(\)\) v\.currentTime = ILK_BAS; \};/);
  assert.match(hero, /if \(t >= DONGU_SON\) \{ ilkTur = false; v\.currentTime = DONGU_BAS; return; \}/);
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
