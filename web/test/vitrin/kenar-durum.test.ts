// 17.10 çok motorlu denetimin (v2.458 sonrası) üç kenar durumu. Kaynak metni okunur (derleme gerekmez); kabuk betiği
// sahte DOM'da çalıştırılır.
//  1) Kabuktaki «Menü» React gelmeden basılınca dokunuş kayboluyordu (createRoot, hydrate değil).
//  2) Geç gelen /v1/dogrulama yanıtı, kullanıcı kaydırmışken sayfayı çapaya geri çekiyordu.
//  3) Çekmece kilidi klasik kaydırma çubuğunu kaldırınca hap ~15 px genişliyor, içerik kayıyordu.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");
const yorumsuz = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const ust = oku("../../src/features/vitrin/UstCubuk.tsx");

/** vite.config'teki kabuk gövde betiği (dize birleştirmeleri çözülerek; hiz.test.ts ile aynı yöntem). */
function kabukBetigi(): string {
  const m = /const betik = ([\s\S]*?)\n\s*(?:if|let|const)\b/.exec(oku("../../vite.config.ts"));
  assert.ok(m, "betik bulunamadı");
  return [...m[1].matchAll(/'([^']*)'|`([^`]*)`/g)].map((p) => (p[1] ?? p[2]).replace("${poster}", "assets/santral-poster-AbC123.webp"))
    .join("").replace(/^<script>/, "").replace(/<\/script>$/, "");
}

type Dinleyici = (e: { target: Oge }) => void;
type Oge = { sinif: string; hidden?: boolean; textContent?: string; oznitelik: Record<string, string>; dinleyiciler: Dinleyici[];
  ata?: Oge; setAttribute(a: string, d: string): void; addEventListener(t: string, f: Dinleyici): void; closest(s: string): Oge | null };

/** Element.closest: yalnız «.sinif» ya da «a» seçicisi, ata zinciri boyunca. */
function enYakin(oge: Oge | undefined, s: string): Oge | null {
  for (; oge; oge = oge.ata) if (s === oge.sinif || s === "." + oge.sinif) return oge;
  return null;
}

/** Kabuk başlığının sahte DOM'u: header.vt-ust > button.vt-menu-dugme + bağlantı, #vt-cekmece > bağlantı. */
function kabuk() {
  const oge = (sinif: string, ata?: Oge, ek: Partial<Oge> = {}): Oge => ({
    sinif, ata, oznitelik: {}, dinleyiciler: [], ...ek,
    setAttribute(a, d) { this.oznitelik[a] = d; },
    addEventListener(t, f) { assert.equal(t, "click"); this.dinleyiciler.push(f); },
    closest(s) { return enYakin(this, s); },
  });
  const baslik = oge("vt-ust");
  const dugme = oge("vt-menu-dugme", baslik, { textContent: "Menü", oznitelik: { "aria-expanded": "false" } });
  const cta = oge("a", baslik);
  const cekmece = oge("vt-cekmece", baslik, { hidden: true });
  const bag = oge("a", cekmece);
  /** Tık hedeften yukarı kabarır (yalnız başlık ağacı). */
  const tikla = (hedef: Oge) => { for (let o: Oge | undefined = hedef; o; o = o.ata) o.dinleyiciler.forEach((f) => f({ target: hedef })); };
  return { baslik, dugme, cta, cekmece, bag, tikla };
}

function calistir(yol: string, jeton: string | null) {
  const k = kabuk();
  const olay = { kokTemizlendi: false, onyukleme: 0 };
  const pencere: { __pvqMenu?: boolean } = {};
  vm.runInNewContext(kabukBetigi(), {
    location: { pathname: yol, search: "" },
    localStorage: { getItem: (a: string) => (a === "pvq_token" ? jeton : null) },
    document: {
      getElementById: (id: string) => (id === "root" ? { set textContent(_: string) { olay.kokTemizlendi = true; } } : id === "vt-cekmece" ? k.cekmece : null),
      querySelector: (s: string) => (s === ".vt-ust .vt-menu-dugme" ? k.dugme : null),
      documentElement: { classList: { add: () => {} } },
      createElement: () => ({}),
      head: { appendChild: () => { olay.onyukleme++; } },
    },
    window: pencere,
  });
  return { ...k, olay, pencere };
}

test("kabuk «Menü»sü React gelmeden çekmeceyi açar/kapatır, durumu window.__pvqMenu'ye yazar", () => {
  const k = calistir("/", null);
  // açılışta hiçbir şeye dokunmaz: yalnız dinleyici takar (ilk boyama ve poster ön yüklemesi aynen)
  assert.equal(k.olay.kokTemizlendi, false);
  assert.equal(k.olay.onyukleme, 1, "poster ön yüklemesi hâlâ yapılıyor");
  assert.equal(k.cekmece.hidden, true);
  assert.equal(k.pencere.__pvqMenu, undefined);

  k.tikla(k.dugme);
  assert.equal(k.cekmece.hidden, false);
  assert.equal(k.dugme.oznitelik["aria-expanded"], "true");
  assert.equal(k.dugme.textContent, "Kapat");
  assert.equal(k.pencere.__pvqMenu, true);

  k.tikla(k.bag);                                    // çekmece bağlantısı (çapa) çekmeceyi kapatır
  assert.equal(k.cekmece.hidden, true);
  assert.equal(k.dugme.textContent, "Menü");
  assert.equal(k.pencere.__pvqMenu, false);

  k.tikla(k.dugme); k.tikla(k.cta);                  // hap CTA'sı da kapatır (React'teki v2.458 davranışı)
  assert.equal(k.pencere.__pvqMenu, false);
  k.tikla(k.dugme); k.tikla(k.dugme);                // ikinci basış kapatır
  assert.equal(k.cekmece.hidden, true);
  assert.equal(k.dugme.oznitelik["aria-expanded"], "false");
});

test("kabuk silinen yollarda (oturumlu kök, /yontem) menü dinleyicisi takılmaz", () => {
  for (const [yol, jeton] of [["/", "j"], ["/yontem", null]] as const) {
    const k = calistir(yol, jeton);
    assert.equal(k.olay.kokTemizlendi, true, yol);
    assert.equal(k.dugme.dinleyiciler.length + k.baslik.dinleyiciler.length, 0, yol);
  }
});

test("UstCubuk kabuk durumunu ilk çizimde bir kez okur; etiketler ve seçiciler kabuk betiğiyle aynı", () => {
  assert.match(ust, /const \[acik, setAcik\] = useState\(\(\) => typeof window !== "undefined" && window\.__pvqMenu === true\);/,
    "kabuk Node'da çizilir (window yok); bayrak yalnız true iken açık başlar");
  assert.match(ust, /useEffect\(\(\) => \{ delete window\.__pvqMenu; \}, \[\]\);/, "bayrak sayfa başına bir kez kullanılır");
  assert.match(ust, /\{acik \? "Kapat" : "Menü"\}/);
  assert.match(kabukBetigi(), /a\?"Kapat":"Menü"/, "kabuk etiketi React'inkiyle aynı");
  assert.match(ust, /className="vt-dugme vt-dugme--cizgi vt-menu-dugme"[\s\S]{0,80}aria-expanded=\{acik\} aria-controls="vt-cekmece"/);
  assert.match(ust, /<div className="vt-cekmece" id="vt-cekmece" ref=\{cekmece\} hidden=\{!acik\}>/);
  assert.match(oku("../../src/features/vitrin/VitrinKabugu.tsx"), /<UstCubuk onPanel=\{\(\) => \{\}\} kip="ana" \/>/);
});

test("çapa yeniden kaydırması kullanıcı oynadıysa yapılmaz (scrollY'ye değil girdiye bakılır)", () => {
  const capa = oku("../../src/features/vitrin/useCapaKaydir.ts");
  const kod = yorumsuz(capa);
  assert.match(kod, /const GIRDILER = \["wheel", "touchstart", "pointerdown", "keydown"\] as const;/);
  assert.match(kod, /window\.addEventListener\(o, isaretle, \{ capture: true, passive: true \}\)/, "edilgen ve yakalama evresinde");
  assert.match(kod, /window\.removeEventListener\(o, isaretle, \{ capture: true \}\)/, "kaldırırken capture eşleşmeli");
  assert.match(kod, /const yeniCapa = \(\) => \{ oynadi\.current = false; \};\n[\s\S]*window\.addEventListener\("hashchange", yeniCapa\)/,
    "sayfa içi çapa tıkı yeni sıçramadır");
  assert.match(kod, /if \(!h \|\| oynadi\.current\) return;/);
  assert.match(kod, /requestAnimationFrame\(\(\) => \{\n\s*if \(!oynadi\.current\) document\.getElementById/, "kare beklerken oynanırsa da vazgeçilir");
  assert.match(kod, /return \(\) => cancelAnimationFrame\(kare\);/);
  assert.match(kod, /\}, \[tetik\]\);/);
  assert.doesNotMatch(kod, /scrollY|pageYOffset/, "kaydırma çapalaması scrollY'yi kendisi oynatır; ölçüt girdi olmalı");
});

test("çekmece kilidi kaydırma çubuğunun yerini korur: html dolgusu + hap payı, kapanınca geri", () => {
  const efekt = /useEffect\(\(\) => \{\s+\/\/ mobil çekmece[\s\S]*?\n {2}\}, \[acik\]\);/.exec(ust)?.[0];
  assert.ok(efekt, "çekmece efekti bulunamadı");
  const kod = yorumsuz(efekt);
  const olcum = kod.indexOf("const cubuk = window.innerWidth - kok.clientWidth;");
  assert.ok(olcum >= 0 && olcum < kod.indexOf('kok.style.overflow = "hidden";'), "çubuk kilitten ÖNCE ölçülür");
  assert.match(kod, /if \(cubuk > 0\) \{\n\s*kok\.style\.paddingRight = `\$\{cubuk\}px`;\n\s*kok\.style\.setProperty\("--vt-kaydirma-payi", `\$\{cubuk\}px`\);\n\s*\}/,
    "kaplama çubukta (dokunmatik) hiçbir şey eklenmez");
  assert.match(kod, /kok\.style\.overflow = oncekiTasma;\n\s*kok\.style\.paddingRight = oncekiDolgu;\n\s*kok\.style\.removeProperty\("--vt-kaydirma-payi"\);/);

  const css = yorumsuz(oku("../../src/features/vitrin/vitrin.css"));
  const kurallar = [...css.matchAll(/(?:^|\n)\s*\.vt-ust \{([^}]*)\}/g)];
  const yuzen = kurallar.findIndex((m) => /position: fixed/.test(m[1]));
  assert.ok(yuzen >= 0, "yüzen .vt-ust kuralı bulunamadı");
  assert.match(kurallar[yuzen][1], /right: var\(--vt-kaydirma-payi, 0px\);/);
  for (const m of kurallar.slice(yuzen + 1)) assert.doesNotMatch(m[1], /\b(right|inset):/, "sonraki .vt-ust kuralı sağ payı ezmemeli");
  // karar: scrollbar-gutter: stable çekmecenin yanında boş şerit bırakıyor ve panel/giriş sayfalarına da dokunuyordu
  for (const d of ["../../src/features/vitrin/vitrin.css", "../../src/index.css"]) assert.doesNotMatch(yorumsuz(oku(d)), /scrollbar-gutter/, d);
});
