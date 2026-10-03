// v2.384 — vitrin yapı kuralları: görünüm .vt kapsamında (panele sızmaz).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";

const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");

/** Seçici listesini yalnız üst düzey virgüllerden böler: `:where(h1, h2)` içindeki virgüller bölünmez. */
function ustDuzeyBol(liste: string): string[] {
  const parcalar: string[] = [];
  let derinlik = 0;
  let bas = 0;
  for (let i = 0; i < liste.length; i++) {
    if (liste[i] === "(") derinlik++;
    else if (liste[i] === ")") derinlik--;
    else if (liste[i] === "," && derinlik === 0) { parcalar.push(liste.slice(bas, i)); bas = i + 1; }
  }
  parcalar.push(liste.slice(bas));
  return parcalar.map((p) => p.trim()).filter(Boolean);
}

test("vitrin.css'teki her seçici .vt ile başlar", () => {
  const css = oku("../../src/features/vitrin/vitrin.css")
    .replace(/\/\*[\s\S]*?\*\//g, "")       // yorumlar
    .replace(/@media[^{]*\{/g, "");         // medya başlıkları (kapanış parantezi seçici üretmez)
  const seciciler = [...css.matchAll(/([^{}]+)\{/g)].flatMap((m) => ustDuzeyBol(m[1]));
  assert.ok(seciciler.length > 40, `seçici sayısı ${seciciler.length}`);
  for (const s of seciciler) assert.ok(s.startsWith(".vt"), `kapsam dışı seçici: ${s}`);
});

test("/yontem artık eski Vitrin sabitlerini kullanmıyor ve tek yöntem kaynağından okuyor", () => {
  const yontem = oku("../../src/features/vitrin/Yontem.tsx");
  assert.doesNotMatch(yontem, /from "\.\/Vitrin"/);
  assert.match(yontem, /from "\.\/yontem-metni"/);
  assert.doesNotMatch(yontem, /style=\{/);
});

test("vitrin bileşenlerinde satır içi stil yok", () => {
  const kok = new URL("../../src/features/vitrin/", import.meta.url);
  for (const ad of readdirSync(kok).filter((a) => a.endsWith(".tsx"))) {
    assert.doesNotMatch(readFileSync(new URL(ad, kok), "utf8"), /style=\{/, ad);
  }
});

test("ana sayfa yeni bileşenlerden kurulur; eski süsler kalktı", () => {
  const vitrin = oku("../../src/features/vitrin/Vitrin.tsx");
  for (const parca of ["<UstCubuk", "<Hero", "<KanitSeridi", "<DortAdim", "<TurkiyePiyasasi", "<AcikKarne durum={durum}", "<Sss", "<Basvuru", "<Altbilgi", "useDogrulama"]) {
    assert.ok(vitrin.includes(parca), parca);
  }
  assert.doesNotMatch(vitrin, /YildizAlani|Dalga|KatmanIkon|export const/);
});

test("kanıt şeridi: uydurma hedef yok; 'yayın açılınca' yalnız kapalı durumda", () => {
  const kanit = oku("../../src/features/vitrin/KanitSeridi.tsx");
  assert.doesNotMatch(kanit, /\?\? 80/);
  assert.match(kanit, /hedef \$\{yuzdeTr\(veri\.bant_hedef_pct\)\}/);
  assert.match(kanit, /\{tur === "kapali" && \(\s*<div className="vt-alanlar">/);
});

test("Türkiye piyasası: elle yazılmış TL ve kurulu güç dipnotu yok", () => {
  const piyasa = oku("../../src/features/vitrin/TurkiyePiyasasi.tsx");
  assert.doesNotMatch(piyasa, /25,4 bin TL|4,5 MW/);
  assert.match(piyasa, /Sapmanın TL karşılığı panelde, kendi santralinizin verisiyle hesaplanır\./);
  assert.match(piyasa, /id="para"/);
});

test("Açık karne: yöntem kutusu tek kaynaktan; yinelenen KPI kutusu yok", () => {
  const karne = oku("../../src/features/vitrin/AcikKarne.tsx");
  assert.match(karne, /from "\.\/yontem-metni"/);
  assert.match(karne, /id="karne"/);
  assert.doesNotMatch(karne, /PANELDEN|Derine inmek/);
  assert.doesNotMatch(karne, /\?\? 80/);
});

test("başvuru: hitap 'siz', bal küpü yerinde, uç aynı; SSS beş soru", () => {
  const basvuru = oku("../../src/features/vitrin/Basvuru.tsx");
  assert.match(basvuru, /Kendi karnenizi başlatın\./);
  assert.match(basvuru, /Karnemi başlat/);
  assert.match(basvuru, /className="vt-bal" tabIndex=\{-1\} aria-hidden="true"/);
  assert.match(basvuru, /api\.vitrinBasvuru\(/);
  assert.match(basvuru, /id="basla"/);
  const tum = readdirSync(new URL("../../src/features/vitrin/", import.meta.url))
    .map((a) => readFileSync(new URL(`../../src/features/vitrin/${a}`, import.meta.url), "utf8")).join("\n");
  assert.doesNotMatch(tum, /Kendi karneni başlat/);
  assert.equal((oku("../../src/features/vitrin/Sss.tsx").match(/^\s*\["/gm) ?? []).length, 5);
});
