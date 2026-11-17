import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");

// 16.11.2026 gezinme hızı partisi — kaynak pinleri (davranış: istemci belleği damgaya bağlı 10 dk; yan menüde ısıtma; Santralim kademe + yarış koruması)
test("istemci belleği 10 dk (damga tazeler), ısıtma beş üretim sayfasını + Genel bakış'ı kapsar", () => {
  const cl = oku("../../src/api/client.ts");
  assert.match(cl, /const BELLEK_MS = 600_000;/);
  assert.match(cl, /export function bellekEskit\(\)/);                     // damga değişince yaş sıfırlanır — tazelik güvencesi bu
  assert.match(cl, /export function isit\(sayfa: string, plantId\?: string\): void/);
  for (const s of ["genel", "santralim", "tahminler", "aylik", "dogruluk", "kalibrasyon", "kgup", "mutabakat", "finans", "sayac", "veri", "olaylar", "takvim"]) assert.match(cl, new RegExp(`\\n  ${s}: \\(p\\) => \\[api\\.`), s);
  assert.match(cl, /finans: \(p\) => \[api\.finansalEtki\(p, donemSecenekleri\("ay"\)\[1\]\?\.kod/);   // sayfanın ilk çağrısıyla aynı dönem → aynı yol
  assert.match(cl, /if \(TABAN == null \|\| !plantId\) return;/);          // örnek kipte ve santralsız ısıtma yok
});

test("yan menü düğmesi niyet anında ısıtır (fare + odak), tıklama davranışı aynı", () => {
  const k = oku("../../src/shell/Kabuk.tsx");
  assert.match(k, /onClick=\{\(\) => \{ setSayfa\(s\.id\); setMenuAcik\(false\); \}\}\n\s+onMouseEnter=\{\(\) => isit\(s\.id, plantId\)\} onFocus=\{\(\) => isit\(s\.id, plantId\)\}/);
});

test("Santralim: her veri efekti yarış korumalı, ikincil kartlar özet gelince başlar", () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /const plantRef = useRef\(plantId\); plantRef\.current = plantId;/);
  assert.ok((s.match(/plantRef\.current/g) ?? []).length >= 20, "yarış koruması sayısı");
  // 17.11 Santralim hız turu: `hazir` kademesi yerine görünürlük kapıları — ilk ekran (özet, seri, PR, sağlık, segment, sensör,
  // kullanılabilirlik) hemen; «Santral» bölümü 2, ayarlar 3, sayfa altı 3 efekt bölge yaklaşınca (useGorunur, 480 px pay)
  assert.doesNotMatch(s, /\bhazir\b/, "eski kademe kalmadı");
  assert.match(s, /const \[santralRef, santralGorunur\] = useGorunur<HTMLElement>\(\);/);
  assert.match(s, /const \[ayarRef, ayarGorunur\] = useGorunur<HTMLDivElement>\(\);/);
  assert.match(s, /const \[altRef, altGorunur\] = useGorunur<HTMLElement>\(\);/);
  assert.equal((s.match(/if \(!santralGorunur\) return;/g) ?? []).length, 2, "santral bölümü kapısı");
  assert.equal((s.match(/if \(!ayarGorunur\) return;/g) ?? []).length, 3, "ayarlar kapısı");
  assert.equal((s.match(/if \(!altGorunur\) return;/g) ?? []).length, 3, "sayfa altı kapısı");
  for (const uc of ["api.pr(plantId)", "api.saglik(plantId)", "api.sensorler(plantId)", "api.dengesizlik(plantId, 14)"])
    assert.ok(s.includes(uc), `ilk ekran ucu hemen: ${uc}`);
  assert.match(s, /<section className="bolum" ref=\{santralRef\}>/); assert.match(s, /<div ref=\{ayarRef\}>/); assert.match(s, /<section className="bolum" ref=\{altRef\}>/);
  assert.match(s, /<SantralimIskeleti ad=\{ad\} \/>/, "sayfaya özel iskelet (başlık gerçek adla anında)");
  const g = oku("../../src/lib/gorunur.ts");
  assert.match(g, /new IntersectionObserver\(/); assert.match(g, /rootMargin: `\$\{payda\} 0px`/); assert.match(g, /if \(typeof IntersectionObserver === "undefined"\) \{ acik\.current = true; setGorunur\(true\); return; \}/); assert.match(g, /const ref = useCallback\(\(el: T \| null\) => \{/, "geri çağrı ref: öğe sonradan bağlanınca gözlemci kurulur");
  // korumasız .then(setX) kalmadı (veri efektlerinde)
  for (const satir of s.split("\n")) if (/useEffect\(\(\) => \{/.test(satir) && /\[plantId/.test(satir)) assert.doesNotMatch(satir, /\.then\(set[A-Za-z]+\)/, "korumasız mount efekti");
});

test("Mutabakat: iki veri yükleyicisi de son-çağrı-kazanır yarış korumalı", () => {
  const m = oku("../../src/features/sayfalar/Mutabakat.tsx");
  assert.equal((m.match(/const canli = useRef\(0\);/g) ?? []).length, 2);
  assert.equal((m.match(/if \(n === canli\.current\) set[KO]\(v\)/g) ?? []).length, 2);
  assert.doesNotMatch(m, /\.then\(set[KO], /);
});

test("Operasyon: Sayaç ve Olay kaydı yükleyicileri son-çağrı-kazanır; Veri yükleme kartları acik bayraklı", () => {
  for (const d of ["Sayac", "Olaylar"]) {
    const s = oku(`../../src/features/sayfalar/${d}.tsx`);
    assert.match(s, /const canli = useRef\(0\);/, d);
    assert.match(s, /const n = \+\+canli\.current;/, d);
    assert.doesNotMatch(s, /\.then\(setO, /, d);
  }
  const dg = oku("../../src/features/sayfalar/Digerleri.tsx");
  assert.match(dg, /let acik = true; api\.epiasUretim\(plantId\)/);
  assert.match(dg, /let acik = true; api\.isler\(\)/);
  // yönetim: Raporlar koşu listesi ve rapor gönderim kartı
  assert.match(dg, /let acik = true; api\.raporGonderim\(plantId\)/);
  assert.match(dg, /api\.kosular\(plantId\)\.then\(\(v\) => \{ if \(acik\) setKosular\(v\); \}\)/);
});

test("Genel bakış: sayfaya özel iskelet dört soru başlığıyla anında; tek uç ve bayat-önce korunur", () => {
  const s = oku("../../src/features/genel/GenelBakis.tsx");
  assert.match(s, /if \(o === undefined\) return <GenelBakisIskeleti \/>;/);
  assert.match(s, /const KART_BASLIKLARI = \["Bugün ne kadar üretim bekleniyor\?", "Yarının üretim programı hazır mı\?", "Açık veri ve operasyon riskleri", "Finansal durum nedir\?"\] as const;/);
  assert.equal((s.match(/baslik=\{KART_BASLIKLARI\[\d\]\}/g) ?? []).length, 4, "dört kart ortak sabitten"); assert.match(s, /const ISKELET_SATIR = \[7, 7, 4, 5\];/);
  assert.match(s, /useState<GenelBakisT \| null \| undefined>\(\(\) => bellekten\.genelBakis\(plantId\)\)/);
  assert.equal((s.match(/api\.genelBakis\(plantId\)/g) ?? []).length, 1, "tek uç");
});

// 17.11 KGÜP hız ve bütünlük turu — kaynak pinleri
test("KGÜP: bayat-önce bellek, sürüm geçmişi yalnız açılınca, iki bölümlü akış ve gövde iskeletleri", () => {
  const s = oku("../../src/features/sayfalar/Kgup.tsx");
  assert.match(s, /useState<KgupOnizleme \| null \| undefined>\(\(\) => bellekten\.kgup\(plantId\)\)/, "önizleme bellekten başlar");
  assert.match(s, /useState<KgupRevizyon \| null \| undefined>\(\(\) => bellekten\.kgupRevizyon\(plantId\)\)/, "revizyon bellekten başlar");
  const efekt = s.slice(s.indexOf("useEffect(() => {"), s.indexOf("}, [plantId, ds]);"));
  assert.doesNotMatch(efekt, /kgupSurumler|surumleriYenile/, "sürüm geçmişi açılış isteği değil (3 → 2 istek)");
  assert.match(efekt, /setKgup\(bellekten\.kgup\(plantId\)\); setRv\(bellekten\.kgupRevizyon\(plantId\)\);/, "santral geçişinde bellekteki anında");
  assert.match(efekt, /setKgup\(\(e\) => \(v \? ayniysaEskisi\(e, v\) : v\)\)/, "aynı veri yeniden çizdirmez");
  assert.match(s, /onToggle=\{\(e\) => \{ if \(\(e\.currentTarget as HTMLDetailsElement\)\.open && surumler === undefined\) surumleriYenile\(\); \}\}/, "açılınca istenir");
  assert.match(s, /<div className="akis">/); assert.equal((s.match(/<section className="bolum">/g) ?? []).length, 2, "Yarın / Bugün bölümleri");
  assert.match(s, /<div className="ozet-bas">Yarın<span className="sag">/); assert.match(s, /<div className="ozet-bas">Bugün<span className="sag">/);
  assert.doesNotMatch(s, /baslik="Üretim programı \(KGÜP\) —/, "kart başlığı sayfa başlığını yinelemez");
  assert.match(s, /kgup === undefined \? \([\s\S]{0,220}<ProgramIskeleti \/>/); assert.match(s, /rv === undefined \? <RevizyonIskeleti \/>/);
  assert.match(s, /function ProgramIskeleti\(\)[\s\S]*?className="program-ozet"[\s\S]*?className="dugme-grubu"/, "iskelet gerçek kalıpta");
  assert.match(s, /Array\.from\(\{ length: 13 \}/, "revizyon iskeleti 13 satır (gün ortası)");
  const cl = oku("../../src/api/client.ts");
  assert.match(cl, /kgup: \(p: string\): KgupOnizleme \| undefined => bellektenOku<KgupOnizleme>\(`\/v1\/plants\/\$\{p\}\/kgup\?fmt=json&kantil=p50`\)/, "bellek yolu kgupOnizleme ile birebir");
  assert.match(cl, /kgupRevizyon: \(p: string\): KgupRevizyon \| undefined => bellektenOku<KgupRevizyon>\(`\/v1\/plants\/\$\{p\}\/kgup\/revizyon`\)/);
  const css = oku("../../src/index.css");
  assert.match(css, /\n\.akis \{ display: grid; gap: 28px; \}/); assert.match(css, /\.akis \.bolum \{ display: grid; gap: 14px;/);
  assert.match(css, /\.iskelet-satirlar \.iskelet-alan \{ height: 28px;/);
});
