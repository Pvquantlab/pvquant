// v2.384 — vitrin yapı kuralları: görünüm .vt kapsamında (panele sızmaz).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { BOLUMLER } from "../../src/features/vitrin/bolumler.ts";

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
    .replace(/@keyframes[^{]*\{(?:[^{}]*\{[^}]*\})*[^{}]*\}/g, "")   // keyframes blokları (from/to seçici değildir)
    .replace(/@(media|starting-style|supports)[^{]*\{/g, "");   // at-rule başlıkları (kapanış parantezi seçici üretmez)
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

test("vitrin bileşenlerinde satır içi stil yok (Rozet.tsx hariç: <use> gölge ağacında sembol vurgusu motor uyumu için satır içi stil ister — BENIOKU §6.3)", () => {
  const kok = new URL("../../src/features/vitrin/", import.meta.url);
  for (const ad of readdirSync(kok).filter((a) => a.endsWith(".tsx") && a !== "Rozet.tsx")) {
    assert.doesNotMatch(readFileSync(new URL(ad, kok), "utf8"), /style=\{/, ad);
  }
});

test("ana sayfa yeni bileşenlerden kurulur; eski süsler kalktı", () => {
  const vitrin = oku("../../src/features/vitrin/Vitrin.tsx");
  for (const parca of ["<UstCubuk", "<Hero", "<BolumCubugu", "<KanitSeridi", "<DortAdim", "<TurkiyePiyasasi", "<IsIzgarasi", "<AcikKarne durum={durum}", "<Sss", "<Basvuru", "<Altbilgi", "useDogrulama"]) {
    assert.ok(vitrin.includes(parca), parca);
  }
  assert.doesNotMatch(vitrin, /YildizAlani|Dalga|KatmanIkon|export const/);
});

test("bölüm çubuğu çapaları gerçek bölümlere, sayfadaki sırayla işaret eder (R30)", () => {
  // Kaynak-metin regex'i yerine modül içe aktarımı: biçim değişse de çapalar sessizce kaçamaz.
  const dosyaE: Record<string, string> = {
    katmanlar: "DortAdim.tsx", para: "TurkiyePiyasasi.tsx", isler: "IsIzgarasi.tsx",
    karne: "AcikKarne.tsx", rakamlar: "DisiplinBandi.tsx", sss: "Sss.tsx", basla: "Basvuru.tsx",
  };
  assert.equal(BOLUMLER.length, 7);
  const vitrin = oku("../../src/features/vitrin/Vitrin.tsx");
  let son = -1;
  for (const [id] of BOLUMLER) {
    const dosya = dosyaE[id];
    assert.ok(dosya, `#${id} için kaynak dosya eşlemesi tanımsız`);
    assert.ok(oku(`../../src/features/vitrin/${dosya}`).includes(`id="${id}"`), `#${id} hedefi ${dosya} içinde yok`);
    const bilesen = "<" + dosya.replace(".tsx", "");
    const yer = vitrin.indexOf(bilesen);
    assert.ok(yer > son, `${bilesen} çubuk sırasıyla sayfa sırası uyuşmuyor (spy "sonuncu kazanır" buna dayanır)`);
    son = yer;
  }
});

test("iş ızgarası: rakamlı vaat ve müşteri iması yok; dört masa fayda kalıbında (R31+Ö8)", () => {
  const is = oku("../../src/features/vitrin/IsIzgarasi.tsx");
  assert.doesNotMatch(is, /%\d|\d+ (bin|milyon) TL|\d+\+? (müşteri|kuruluş|proje)|1200|9 ?000/i);
  assert.match(is, /#para/);
  assert.match(is, /#karne/);
  assert.match(is, /\/yontem/);
  assert.match(is, /Dördü de bugün panelde\./);        // Ö14: olumlu kurgu, «yol haritası değil» kalktı
  for (const masa of ["Program teslimi", "Ticaret masası", "Operasyon nöbeti", "Finansman dosyası"]) {
    assert.ok(is.includes(masa), masa);
  }
  assert.match(is, /vt-is__kunye/);                    // etiket–değer künyesi kalıbın parçası
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

test("başvuru: hitap 'siz', bal küpü yerinde, uç aynı; SSS altı soru (Ö13 güven sorusu dahil)", () => {
  const basvuru = oku("../../src/features/vitrin/Basvuru.tsx");
  assert.match(basvuru, /Karnenizi başlatın\./);       // eylem sözlüğü (Ö2): her yüzeyde tek ad
  // eski eylem adı hiçbir vitrin yüzeyine geri dönmesin (inceleme: /yontem'de atlanmıştı)
  for (const d of readdirSync(new URL("../../src/features/vitrin", import.meta.url)))
    if (/\.(tsx?|css)$/.test(d))
      assert.doesNotMatch(oku(`../../src/features/vitrin/${d}`), /Kendi karnenizi/, d);
  assert.match(basvuru, /Karnemi başlat/);
  assert.match(basvuru, /className="vt-bal" tabIndex=\{-1\} aria-hidden="true"/);
  assert.match(basvuru, /api\.vitrinBasvuru\(/);
  assert.match(basvuru, /id="basla"/);
  const vitrinKok = new URL("../../src/features/vitrin/", import.meta.url);
  const tum = readdirSync(vitrinKok, { withFileTypes: true })
    .filter((g) => g.isFile())
    .map((g) => readFileSync(new URL(g.name, vitrinKok), "utf8")).join("\n");
  assert.doesNotMatch(tum, /Kendi karneni başlat/);
  assert.equal((oku("../../src/features/vitrin/Sss.tsx").match(/^\s*\["/gm) ?? []).length, 6);
  assert.match(oku("../../src/features/vitrin/Sss.tsx"), /Modelinize neden güvenelim\?/);
});

test("disiplin dipnotu otomasyon iddia etmez; sayım kuralını açıkça söyler (inceleme C1)", () => {
  const db = oku("../../src/features/vitrin/DisiplinBandi.tsx");
  assert.doesNotMatch(db, /elle yazılmaz|koşusundan okunur|CI'dan okunur/);
  assert.match(db, /aşağı yuvarlanmış/);
  assert.match(db, /id="vt-dipnot-1"/);
  assert.match(db, /href=\{hedef\}|#vt-dipnot-1/);
});

test("TL kartları «panel kesiti»: tek yüzey, beş kart, eski vinyet ve sembol ikon yok; amber yalnız gerçekleşen çiziminde (kart-tasarim)", () => {
  const piyasa = oku("../../src/features/vitrin/TurkiyePiyasasi.tsx");
  assert.match(piyasa, /className="vt-kesit"/);
  assert.equal((piyasa.match(/^\s*\{ ad: "/gm) ?? []).length, 5);
  assert.doesNotMatch(piyasa, /vinyet-|VinyetTl|VinyetTicaret|vt-vin-kart|tek tık/i);
  const cizim = oku("../../src/features/vitrin/KartCizimleri.tsx");
  // veri renk sözleşmesi: amber (#C27803) yalnız sapma (gerçekleşen eğrisi) ve alarm (gelen ölçüm) çizimlerinde
  const amberli = [...cizim.matchAll(/export function (\w+)\(\)[\s\S]*?(?=export function|$)/g)]
    .filter((m) => m[0].includes("#C27803")).map((m) => m[1]);
  assert.deepEqual(amberli, ["CizimSapma", "CizimAlarm"]);
  assert.doesNotMatch(cizim, /#FFB4A2|#B11F47/i);   // şeftali ve eylem rengi kart çizimlerinde yok
});
