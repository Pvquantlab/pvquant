// 17.10 (v2.458) — başlık tıklanabilirlik sözleşmesi. .vt-ust (yüzen hap) pointer-events: none taşır ve bu
// özellik MİRAS alınır: başlığın doğrudan çocuğu olan her tıklama yüzeyi (hap, çekmece, mega örtüsü) tıklamayı
// kendisi geri almazsa ölüdür. v2.432–v2.457: mobil çekmece bağlantıları tıklanamıyordu; mega örtüsü dış tıkı
// alttaki sayfaya sızdırıyordu. Kaynak metni okunur (derleme gerekmez).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");
const css = oku("../../src/features/vitrin/vitrin.css").replace(/\/\*[\s\S]*?\*\//g, "");   // yorumlar sayılmaz
const ust = oku("../../src/features/vitrin/UstCubuk.tsx");
const kac = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** <header className="vt-ust"> içindeki DOĞRUDAN çocukların (6 boşluk girinti) ayırt edici vt- sınıfı. */
function baslikCocuklari(): string[] {
  const bas = ust.indexOf('<header className="vt-ust">');
  const son = ust.indexOf("</header>", bas);
  assert.ok(bas >= 0 && son > bas, '<header className="vt-ust"> bulunamadı');
  return [...ust.slice(bas, son).matchAll(/^ {6}(?:\{[^<\n]*)?<[a-z]+\b[^>]*?className="([^"]+)"/gm)]
    .map((m) => m[1].split(/\s+/).find((s) => s.startsWith("vt-") && s !== "vt-kap"))
    .filter((s): s is string => s !== undefined);
}

/** `.sinif` öznesine (ardından yalnız durum sınıfı/öznitelik) pointer-events: <deger> veren kuralların konumları. */
function kurallar(sinif: string, deger: "auto" | "none"): number[] {
  const re = new RegExp(`\\.${kac(sinif)}(?![\\w-])(?:\\.[\\w-]+|\\[[^\\]]*\\])*\\s*\\{[^}]*pointer-events:\\s*${deger}\\b`, "g");
  return [...css.matchAll(re)].map((m) => m.index ?? -1);
}

test("başlığın doğrudan çocukları pointer-events: none mirasını .vt-ust kuralından SONRA geri alır", () => {
  const ustNone = kurallar("vt-ust", "none");
  assert.ok(ustNone.length > 0, ".vt-ust artık pointer-events: none taşımıyor — bu sözleşmeyi gözden geçirin");
  const cocuklar = baslikCocuklari();
  assert.deepEqual([...cocuklar].sort(), ["vt-cekmece", "vt-mega-ortu", "vt-ust__ic"],
    "başlığa yeni doğrudan çocuk eklendi: tıklama yüzeyiyse pointer-events: auto almalı ve bu listeye eklenmeli");
  for (const sinif of cocuklar) {
    const auto = kurallar(sinif, "auto").filter((i) => i > Math.max(...ustNone));
    assert.ok(auto.length > 0, `.${sinif} .vt-ust'ün pointer-events: none'unu miras alıyor — tık alttaki sayfaya düşer`);
    assert.equal(kurallar(sinif, "none").filter((i) => i > Math.max(...auto)).length, 0, `.${sinif} sonradan yeniden tıklanamaz yapılıyor`);
  }
});

test("mega örtüsü tıkı yakalarken hap (ve içindeki panel) örtünün üstünde kalır", () => {
  // .vt-ust__ic backdrop-filter ile kendi istif bağlamını kurar; .vt-mega onun İÇİNDE kalır. Örtü tık alınca hap
  // pozitif z-index'le örtünün üstüne çıkmazsa hap düğmeleri ve panel bağlantıları ölür.
  const ortuZ = Number(/\.vt-mega-ortu \{[^}]*z-index: (\d+)/.exec(css)?.[1]);
  assert.ok(ortuZ > 0, ".vt-mega-ortu z-index bulunamadı");
  const hap = [...css.matchAll(/\.vt-ust__ic \{[^}]*\}/g)].map((m) => m[0]);
  assert.ok(hap.some((k) => /position: (relative|absolute|fixed|sticky)/.test(k)), ".vt-ust__ic konumlandırılmamış (z-index işlemez)");
  const hapZ = hap.map((k) => Number(/z-index: (\d+)/.exec(k)?.[1] ?? -1));
  assert.ok(Math.max(...hapZ) > ortuZ, `.vt-ust__ic z-index'i örtününkinden (${ortuZ}) büyük olmalı`);
});

test("örtüye inen basış paneli belge dinleyicisinde kapatmaz (dokunmatikte tık sayfaya düşmesin)", () => {
  const tik = /const tik = \(e: PointerEvent\) => \{[\s\S]*?\n {4}\};/.exec(ust)?.[0];
  assert.ok(tik, "dış basış dinleyicisi (const tik) bulunamadı");
  assert.match(tik, /closest\("\.vt-mega-ortu"\)\) return;/);
});

test("çekmece açıkken hap içindeki «Karnenizi başlatın» çekmeceyi kapatır (aynı çapada hashchange gelmez)", () => {
  const cta = ust.split("\n").find((s) => s.includes("vt-dugme--dolu") && s.includes("Karnenizi başlatın"));
  assert.ok(cta, "hap CTA'sı bulunamadı");
  assert.match(cta, /onClick=\{\(\) => setAcik\(false\)\}/);
});
