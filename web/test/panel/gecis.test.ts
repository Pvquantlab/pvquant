// 24.10.2026 — Açık tema panel geçiş turu: sayfa geçişlerinin veri beklemeden tepki vermesi sözleşmeleri.
// Kaynak metni okunur (derleme gerekmez). Kök nedenler ve ölçüm: docs/PANEL-TUR8-2026-10-24.md.
//  1. Veri kapısı yok: hiçbir panel sayfası birden çok isteği Promise.allSettled/Promise.all ile tek kapıda
//     bekletip iskeleti en yavaş yanıta kadar tutmaz (Doğruluk 7, Kalibrasyon 5, Aylık 3, Tahminler 5 istekti).
//  2. Bayat-önce: sayfa durumu bellekten (bellekten.*) başlatılır; 60 sn içinde dönüşte anında çizilir.
//  3. Yoldaki veri için yer tutucu (YerTutucu) — «henüz yok / alınamadı» metni yanıt gelmeden yazılmaz.
//  4. Tema gözlemcileri yalnız data-tema'yı izler (kabuğun .tema-gecisi sınıfı grafiği üç kez kurdurmaz).
//  5. Kahraman grafiğin girdileri hafızalı: inline map/nesne yok (her render'da option yeniden kurulmasın).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const oku = (yol: string) => readFileSync(new URL("../../src/" + yol, import.meta.url), "utf8");
const yorumsuz = (k: string) => k.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`])\/\/[^\n]*/g, "$1");

const SAYFALAR = {
  "features/sayfalar/Dogruluk.tsx": { bellekten: "bellekten.karne(", yerTutucu: true },
  "features/sayfalar/Digerleri.tsx": { bellekten: "bellekten.kalibrasyon(", yerTutucu: true },
  "features/sayfalar/Aylik.tsx": { bellekten: "bellekten.aylik(", yerTutucu: true },
  "features/sayfalar/Tahminler.tsx": { bellekten: "bellekten.tahmin(", yerTutucu: true },
  "features/sayfalar/Portfoy.tsx": { bellekten: "bellektenOku", yerTutucu: true },
  "features/santralim/Santralim.tsx": { bellekten: "bellekten.ozet(", yerTutucu: false },   // istekleri zaten bağımsız; yalnız bayat-önce
  "features/sayfalar/Hakkinda.tsx": { bellekten: 'bellektenOku<HakkindaT>("/v1/hakkinda")', yerTutucu: true },
};

test("panel sayfalarında tek kapı (Promise.allSettled / Promise.all) yok", () => {
  for (const yol of Object.keys(SAYFALAR)) {
    const k = yorumsuz(oku(yol));
    assert.doesNotMatch(k, /Promise\.allSettled\(|Promise\.all\(/, `${yol}: istekler bağımsız olmalı — en yavaş yanıt sayfayı bekletmesin`);
  }
});

test("veri sayfaları bellekten (bayat-önce) başlar ve yoldaki veri için YerTutucu kullanır", () => {
  for (const [yol, b] of Object.entries(SAYFALAR)) {
    const k = yorumsuz(oku(yol));
    assert.ok(k.includes(b.bellekten), `${yol}: ${b.bellekten} ile başlangıç durumu bellekten okunmalı`);
    if (b.yerTutucu) assert.match(k, /<YerTutucu yukseklik=\{\d+\} \/>/, `${yol}: yoldaki veri için YerTutucu`);
    // taze yanıt bayatla birebir aynıysa eski referans korunur → grafik seçenekleri yeniden kurulmaz (4× CPU bulgusu)
    if (yol !== "features/sayfalar/Portfoy.tsx") assert.ok(k.includes("ayniysaEskisi("), `${yol}: tazeleme ayniysaEskisi ile`);
  }
});

test("ayniysaEskisi: birebir aynı veri eski referansı döndürür, farklı veri taze değeri", () => {
  const c = yorumsuz(oku("api/client.ts"));
  assert.match(c, /export function ayniysaEskisi<T>\(eski: T \| null \| undefined, yeni: T\): T/);
  // saf fonksiyon: kaynaktan çıkarılıp çalıştırılır (derleme gerekmez)
  const govde = c.slice(c.indexOf("export function ayniysaEskisi"), c.indexOf("\n}\n", c.indexOf("export function ayniysaEskisi")) + 3)
    .replace("export function ayniysaEskisi<T>(eski: T | null | undefined, yeni: T): T", "function ayniysaEskisi(eski, yeni)").replace(/\(eski as T\)/, "eski");
  const f = new Function(govde + "; return ayniysaEskisi;")() as <T>(e: T | null | undefined, y: T) => T;
  const eski = { a: 1, b: [1, 2] };
  assert.equal(f(eski, { a: 1, b: [1, 2] }), eski, "aynı içerik → eski referans");
  const yeni = { a: 2, b: [1, 2] };
  assert.equal(f(eski, yeni), yeni, "farklı içerik → taze");
  assert.equal(f(undefined, yeni), yeni); assert.equal(f(null, yeni), yeni);
});

test("Tahminler: KGÜP ve kısa ufuk kartları yanıt gelmeden «henüz yok» demez; seri/özet alınamazsa boş durum", () => {
  const k = yorumsuz(oku("features/sayfalar/Tahminler.tsx"));
  assert.match(k, /kgup === undefined \?[\s\S]{0,200}<YerTutucu/, "KGÜP yoldayken yer tutucu");
  assert.match(k, /nc === undefined \? <YerTutucu/, "kısa ufuk yoldayken yer tutucu");
  assert.match(k, /kgup === undefined \? "hesaplanıyor" : "tahmin bekleniyor"/, "KGÜP çipi yolda/yok ayrımı");
  assert.ok(k.includes("Tahmin gösterilemiyor"), "seri ya da özet alınamayınca boş durum");
  assert.doesNotMatch(k, /if \(!seri \|\| !ozet\) return/, "alınamadı durumu sayfayı boş bırakmaz; başlık ve sekme kalır");
});

test("Doğruluk: iki WMAPE paneli hafızalı (her render'da yeni option kurulmaz)", () => {
  const k = yorumsuz(oku("features/sayfalar/Dogruluk.tsx"));
  assert.match(k, /const wmape024 = useMemo\(\(\) => wmapePanel\("0-24"\), \[wmapePanel\]\)/);
  assert.match(k, /const wmape2472 = useMemo\(\(\) => wmapePanel\("24-72"\), \[wmapePanel\]\)/);
  assert.doesNotMatch(k, /option=\{wmapePanel\(/, "EChart'a doğrudan wmapePanel(...) çağrısı verilmez");
});

test("tema gözlemcileri yalnız data-tema'yı izler", () => {
  const t = yorumsuz(oku("lib/useTema.ts"));
  assert.match(t, /observe\(document\.documentElement, \{ attributes: true, attributeFilter: \["data-tema"\] \}\)/);
  const g = yorumsuz(oku("features/sayfalar/ProductionForecastChart.tsx"));
  assert.match(g, /attributeFilter: \["data-tema"\]/);
  assert.doesNotMatch(g, /attributeFilter: \["data-tema", "class"\]/, "class (tema-gecisi) tetiklemez");
});

test("kahraman grafiğin girdileri hafızalı; features sabit nesne", () => {
  for (const yol of ["features/sayfalar/Tahminler.tsx", "features/santralim/Santralim.tsx"]) {
    const k = yorumsuz(oku(yol));
    assert.match(k, /const GRAFIK_OZELLIKLERI = \{ exportButtons: true \} as const/, `${yol}: features sabiti`);
    assert.match(k, /features=\{GRAFIK_OZELLIKLERI\}/, `${yol}: features sabit referans`);
    assert.doesNotMatch(k, /features=\{\{/, `${yol}: inline features nesnesi yok`);
    assert.doesNotMatch(k, /forecast=\{dilim\.saatlik\.map/, `${yol}: inline forecast map yok`);
    assert.doesNotMatch(k, /plant=\{\{/, `${yol}: inline plant nesnesi yok`);
    for (const ad of ["grafikTahmin", "grafikGercek", "grafikSantral"]) {
      assert.match(k, new RegExp(`const ${ad} = useMemo<`), `${yol}: ${ad} useMemo`);
    }
  }
});

test("istemci: bellekten.* okuyucuları aynı yolu bellekte arar (API sözleşmesi değişmedi)", () => {
  const c = yorumsuz(oku("api/client.ts"));
  assert.match(c, /export const bellekten = \{/);
  for (const yol of ["/summary", "/forecast?hours=", "/skill?bucket=0-24", "/skill?bucket=24-72", "/kalibrasyon", "/monthly"]) {
    assert.ok(c.includes(yol), `bellekten: ${yol}`);
  }
  // bellekten okumak ağa çıkmaz
  const govde = c.slice(c.indexOf("export const bellekten = {"), c.indexOf("};", c.indexOf("export const bellekten = {")));
  assert.doesNotMatch(govde, /fetch\(|istek\(|al\(/, "bellekten yalnız bellektenOku kullanır");
});
