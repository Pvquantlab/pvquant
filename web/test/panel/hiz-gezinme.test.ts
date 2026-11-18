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

// 18.11 DSG ve portföyler hız ve bütünlük turu — kaynak pinleri
test("DSG ve portföyler: bayat-önce dokuz okuyucu, üyelik formu açılınca, sapma ozet=1, dört bölümlü akış, KPI 2×2 kapsayıcı kuralı, sayfaya özel iskelet", () => {
  const s = oku("../../src/features/sayfalar/Portfoyler.tsx");
  assert.match(s, /useState<Yuk<PortfoyKisa\[\]>>\(\(\) => bellekten\.portfoyler\(\)\)/, "liste bellekten başlar");
  for (const ad of ["portfoyDetay(secili)", "portfoylerTahmin(secili, 7)", "portfoySapma(secili, kod)", "portfoyRisk(secili, 2)", "portfoyDsgPerspektif(secili, kod)", "portfoyRevizyon(secili, hedef)", "portfoyFinans(secili, kod)"])
    assert.equal((s.split(`bellekten.${ad}`).length - 1), 2, `${ad}: başlangıç + efekt`);
  assert.doesNotMatch(s, /setDetay\(undefined\); setTahmin\(undefined\)/, "santral/dönem geçişinde iskelete düşmez");
  assert.match(s, /\{uyelikAcik && <UyelikFormu /, "üyelik formu (santral listesi isteği) yalnız açılınca");
  assert.doesNotMatch(s, /SayfaIskeleti/, "genel iskelet yerine sayfaya özel");
  assert.match(s, /if \(liste === undefined\) return <Sayfa baslik="Portföy yönetimi" alt=\{alt\}><PortfoylerIskeleti \/><\/Sayfa>;/);
  assert.equal((s.match(/<section className="bolum">/g) ?? []).length, 4 + 2, "4 bölüm + iskelette 2");
  for (const b of ["Dönem", "Önümüzdeki günler", "Üyelik ve finans", "Kayıtlar"]) assert.match(s, new RegExp(`<div className="ozet-bas">${b}<span className="sag">`), b);
  assert.doesNotMatch(s, /ızgara-cift/, "çiftler .sira-2 (Santralim ile aynı)"); assert.equal((s.match(/<div className="sira-2">/g) ?? []).length, 3);
  const cl = oku("../../src/api/client.ts");
  assert.match(cl, /sapma\?ozet=1\$\{donem \? `&donem=/, "sapma ozet=1 (saatlik liste gelmez)");
  assert.match(cl, /portfoySapma: \(id: string, donem\?: string \| null\): PortfoySapmaT \| undefined => bellektenOku<PortfoySapmaT>\(`\/v1\/portfoyler\/\$\{id\}\/sapma\?ozet=1/, "bellek yolu api ile birebir");
  assert.match(cl, /portfoyler: \(\) => \{ const pf = localStorage\.getItem\("pvq_portfoy"\);/, "ısıtma hatırlanan portföyün açılış uçlarını kapsar");
  const css = oku("../../src/index.css");
  assert.match(css, /\.akis \.bolum \{ container-type: inline-size; \}/);
  assert.match(css, /@container \(min-width: 700px\) and \(max-width: 1000px\) \{ \.akis \.satir-4 \{ grid-template-columns: repeat\(2, minmax\(0, 1fr\)\); \} \}/);
});

// 18.11 UI denetimi Grup 1 — Doğruluk: altı yanıt bayat-önce, iki görünürlük kapısı, beş bölümlü akış, sayfaya özel iskelet
test("Doğruluk: bayat-önce altı okuyucu, güvenilirlik ve uzlaştırma kapılı, .akis bölümleri, DogrulukIskeleti", () => {
  const s = oku("../../src/features/sayfalar/Dogruluk.tsx");
  for (const [ad, n] of [["hataDagilimi(plantId)", 3], ["konformal(plantId)", 2], ["backtest(plantId)", 2], ["dengesizlik(plantId)", 3], ["guvenilirlik(plantId)", 3]] as const) assert.equal((s.split(`bellekten.${ad}`).length - 1), n, `${ad}: başlangıç + ana efekt (+ kapılı efekt)`);
  assert.match(s, /useState<BagimsizDogrulama \| null \| undefined>\(\(\) => bellekten\.bagimsizDogrulama\(plantId, donem, bdKural\)\)/);
  assert.match(s, /const \[ortaRef, ortaGorunur\] = useGorunur<HTMLElement>\(\);/);
  assert.match(s, /setBd\(bellekten\.bagimsizDogrulama\(plantId, donem, bdKural\)\)/);
  assert.match(s, /const \[altRef, altGorunur\] = useGorunur<HTMLElement>\(\);/);
  assert.match(s, /if \(!ortaGorunur\) return;[\s\S]{0,120}api\.guvenilirlik\(plantId\)/, "güvenilirlik yalnız kart görünür olunca");
  assert.match(s, /if \(!altGorunur\) return;[\s\S]{0,200}api\.dengesizlik\(plantId\)[\s\S]{0,200}api\.hataDagilimi\(plantId\)/, "uzlaştırma + dağılım yalnız görünür olunca");
  const ana = s.slice(s.indexOf("api.karne(plantId, donem).then((v) => { if (acik)"), s.indexOf("}, [plantId, ds]);"));
  assert.doesNotMatch(ana, /api\.(guvenilirlik|dengesizlik|hataDagilimi)\(/, "ana efekt yalnız karne, konformal, backtest");
  assert.match(s, /if \(!hazir\) return <DogrulukIskeleti \/>;/); assert.doesNotMatch(s, /SayfaIskeleti/);
  assert.equal((s.match(/<section className="bolum"/g) ?? []).length, 5 + 2, "5 bölüm + iskelette 2");
  for (const b of ["Dönem özeti", "Bağımsız doğrulama", "Günlük hata ve aralık", "Uzlaştırma", "Dağılım"]) assert.match(s, new RegExp(`<div className="ozet-bas">${b}<span className="sag">`), b);
  const cl = oku("../../src/api/client.ts");
  assert.match(cl, /guvenilirlik: \(p: string, gun = 60\): Guvenilirlik \| undefined => bellektenOku<Guvenilirlik>\(`\/v1\/plants\/\$\{p\}\/guvenilirlik\?gun=\$\{gun\}`\)/);
  assert.match(cl, /hataDagilimi: \(p: string, gun = 120\): HataDagilimi \| undefined => bellektenOku<HataDagilimi>\(`\/v1\/plants\/\$\{p\}\/hata-dagilimi\?gun=\$\{gun\}&kova=0-24`\)/);
});

// 18.11 UI denetimi Grup 1 — Aylık: üç yanıt daha bayat-önce, dört bölümlü akış, sayfaya özel iskelet
test("Aylık: bankable/P-değerleri/performans bayat-önce, .akis dört bölüm, AylikIskeleti", () => {
  const s = oku("../../src/features/sayfalar/Aylik.tsx");
  for (const ad of ["bankable(plantId)", "pDegerleri(plantId)", "performans(plantId)"]) assert.equal((s.split(`bellekten.${ad}`).length - 1), 2, `${ad}: başlangıç + efekt`);
  assert.doesNotMatch(s, /setBk\(undefined\)|setPd\(undefined\)|setPf\(undefined\)/, "santral geçişinde yer tutucuya düşmez");
  assert.match(s, /setBk\(\(e\) => ayniysaEskisi\(e, v\)\)/); assert.doesNotMatch(s, /SayfaIskeleti/);
  assert.match(s, /if \(!hazir\) return <AylikIskeleti \/>;/);
  assert.equal((s.match(/<section className="bolum">/g) ?? []).length, 4 + 1, "4 bölüm + iskelette 1");
  for (const b of ["Bu ay ve yıl", "Yıl yıl ve performans", "İklim arşivi", "Gerçekleşen"]) assert.match(s, new RegExp(`<div className="ozet-bas">${b}<span className="sag">`), b);
  const cl = oku("../../src/api/client.ts");
  assert.match(cl, /performans: \(p: string, ay = 12\): Performans \| undefined => bellektenOku<Performans>\(`\/v1\/plants\/\$\{p\}\/performans\?ay=\$\{ay\}`\)/);
});

// 18.11 UI denetimi Grup 1 — Kalibrasyon: altı teşhis yanıtı bayat-önce, dört bölümlü akış, sayfaya özel iskelet, başlık yinelemesi yok
test("Kalibrasyon: hijyen/kayma/kayıp ağacı/güç matrisi/saat profili/kayıp ayrışımı bayat-önce, .akis dört bölüm, KalibrasyonIskeleti", () => {
  const s = oku("../../src/features/sayfalar/Digerleri.tsx");
  const K = s.slice(s.indexOf("export function Kalibrasyon("), s.indexOf("function KalibrasyonIskeleti()"));
  for (const ad of ["hijyen(plantId)", "kayma(plantId)", "kayipAgaci(plantId)", "gucMatrisi(plantId)", "saatProfili(plantId)", "kayipAyrisimi(plantId)"]) assert.equal((K.split(`bellekten.${ad}`).length - 1), 2, `${ad}: başlangıç + efekt`);
  assert.doesNotMatch(K, /setHj\(undefined\)|setKy\(undefined\)|setSp\(undefined\)/, "santral geçişinde yer tutucuya düşmez");
  assert.match(K, /if \(!yuklendi\) return <KalibrasyonIskeleti \/>;/);
  assert.equal((K.match(/<section className="bolum">/g) ?? []).length, 4, "4 bölüm");
  for (const b of ["Sonuç", "Veri kalitesi", "Teşhis", "Tipik yıl"]) assert.match(K, new RegExp(`<div className="ozet-bas">${b}<span className="sag">`), b);
  assert.doesNotMatch(K, /baslik="Kalibrasyon sonuçları"|baslik="Kalibrasyonun etkisi"/, "kart başlığı sayfa başlığını yinelemez");
  assert.match(K, /baslik="Katsayılar ve dönem"/); assert.match(K, /baslik="Etkisi" alt="Fiziksel modelden kalibre modele"/);
  const cl = oku("../../src/api/client.ts");
  assert.match(cl, /saatProfili: \(p: string, gun = 30\): SaatProfili \| undefined => bellektenOku<SaatProfili>\(`\/v1\/plants\/\$\{p\}\/saat-profili\?gun=\$\{gun\}&kova=0-24`\)/);
});

// 18.11 UI denetimi Grup 1 — Takvim: tek yanıt bayat-önce, dört bölümlü akış, sayfaya özel iskelet
test("Takvim: bayat-önce, .akis dört bölüm, TakvimIskeleti", () => {
  const s = oku("../../src/features/sayfalar/Takvim.tsx");
  assert.equal((s.split("bellekten.takvim(plantId)").length - 1), 2, "başlangıç + efekt");
  assert.doesNotMatch(s, /setT\(undefined\)/, "santral geçişinde iskelete düşmez");
  assert.match(s, /setT\(\(e\) => ayniysaEskisi\(e, v\)\)/); assert.doesNotMatch(s, /SayfaIskeleti/);
  assert.match(s, /if \(t === undefined\) return <TakvimIskeleti \/>;/);
  assert.equal((s.match(/<section className="bolum">/g) ?? []).length, 4 + 3, "4 bölüm + iskelette 3");
  for (const b of ["Yaklaşan", "Uyum", "Dönem ve gün", "Santral tarihleri"]) assert.match(s, new RegExp(`<div className="ozet-bas">${b}<span className="sag">`), b);
  const cl = oku("../../src/api/client.ts");
  assert.match(cl, /takvim: \(p: string, gun = 90\): Takvim \| undefined => bellektenOku<Takvim>\(`\/v1\/plants\/\$\{p\}\/takvim\?gun=\$\{gun\}`\)/, "bellek yolu api.takvim ile birebir");
});

// 18.11 UI denetimi Grup 1 — Mutabakat: özet + saatlik kıyas bayat-önce (yol kurucu ortak), dört bölümlü akış, .sira-2 çift, sayfaya özel iskelet
test("Mutabakat: bayat-önce iki okuyucu (ortak yol kurucu), .akis dört bölüm, MutabakatIskeleti", () => {
  const s = oku("../../src/features/sayfalar/Mutabakat.tsx");
  assert.equal((s.split("bellekten.mutabakat(plantId, donem, surum, uretim)").length - 1), 2, "özet: başlangıç + efekt");
  assert.equal((s.split("bellekten.saatlikKiyas(plantId, donem, uretim)").length - 1), 2, "saatlik: başlangıç + efekt");
  assert.doesNotMatch(s, /setO\(undefined\)|setK\(undefined\)/, "geçişte iskelete düşmez");
  assert.match(s, /if \(o === undefined\) return <MutabakatIskeleti \/>;/); assert.doesNotMatch(s, /SayfaIskeleti|ızgara-cift/);
  assert.equal((s.match(/<section className="bolum">/g) ?? []).length, 4 + 2, "4 bölüm + iskelette 2");
  for (const b of ["Dönem özeti", "Bildirim ve girdiler", "Kalem kalem", "Saat saat"]) assert.match(s, new RegExp(`<div className="ozet-bas">${b}<span className="sag">`), b);
  const cl = oku("../../src/api/client.ts");
  assert.match(cl, /function mutabakatYolu\(p: string, donem\?: string \| null, surum\?: string \| null, uretim\?: string \| null\): string/);
  assert.equal((cl.match(/mutabakatYolu\(p, donem, surum, uretim\)/g) ?? []).length, 2, "api.mutabakat ve bellekten.mutabakat aynı yolu kurar");
  assert.equal((cl.match(/saatlikKiyasYolu\(p, donem, uretim\)/g) ?? []).length, 2);
});

// 18.11 UI denetimi Grup 1 — Finansal etki: sonuç/senaryo bayat-önce (ortak yol kurucu), dört bölümlü akış, .sira-2 çiftler, sayfaya özel iskelet
test("Finansal etki: bayat-önce (program ve senaryo yolu), .akis dört bölüm, FinansalEtkiIskeleti", () => {
  const s = oku("../../src/features/sayfalar/FinansalEtki.tsx");
  assert.match(s, /const bellektekiSonuc = \(plantId: string, kod: string, uretim: string \| null, pozisyon: "program" \| "uretim"\) =>\n  pozisyon === "program" \? bellekten\.finansalEtki\(plantId, kod, uretim\) : bellekten\.finansalEtkiSenaryo\(plantId, kod, pozisyon, null, uretim\);/);
  assert.equal((s.split("bellektekiSonuc(plantId, kod, uretim, pozisyon)").length - 1), 2, "başlangıç + efekt (bileşen dışı saf yardımcı; efekt bağımlılığı yok)");
  assert.doesNotMatch(s, /setO\(undefined\)/, "geçişte iskelete düşmez"); assert.match(s, /setO\(\(e\) => e \?\? null\)/, "tazeleme düşerse bellekteki kalır");
  assert.match(s, /if \(o === undefined\) return <FinansalEtkiIskeleti secici=\{secici\} \/>;/); assert.doesNotMatch(s, /SayfaIskeleti|ızgara-cift/);
  assert.equal((s.match(/<section className="bolum">/g) ?? []).length, 4 + 1, "4 bölüm + iskelette 1");
  for (const b of ["Dönem", "Karşılaştırma ve eylem", "Düşüklük ve ileriye", "Hesap"]) assert.match(s, new RegExp(`<div className="ozet-bas">${b}<span className="sag">`), b);
  assert.equal((s.match(/alt=\{SAYFA_ALT\}/g) ?? []).length, 2, "sayfa ve iskelet aynı açıklama");
  const cl = oku("../../src/api/client.ts");
  assert.equal((cl.match(/finansalEtkiYolu\(p, donem, uretim/g) ?? []).length, 2, "api.finansalEtki ve bellekten.finansalEtki aynı yolu kurar");
  assert.equal((cl.match(/finansalEtkiSenaryoYolu\(p, donem, pozisyon, sabitMwh, uretim\)/g) ?? []).length, 2);
});

// 18.11 UI denetimi Grup 2 — 375 px: kart başlığı müşteri yüzünde de sarar; etiket + girdi kapsayıcıdan taşmaz (genel kural)
test("Grup 2 CSS: ≤560'ta .kart-bas sarar ve başlık en az %60; .girdi-etiket ve içindeki .girdi kapsayıcıya sığar", () => {
  const css = oku("../../src/index.css");
  const blok = css.slice(css.indexOf("@media (max-width: 560px) {\n  /* 18.11 Grup 2"), css.indexOf("@media (max-width: 560px) {\n  /* 18.11 Grup 2") + 700);
  assert.match(blok, /\n  \.kart-bas \{ flex-wrap: wrap; \}\n  \.kart-baslik \{ flex: 1 1 60%; \}/);
  assert.match(css, /\.girdi-etiket \{ display: flex; flex-direction: column; gap: 5px; font-size: var\(--t-ikincil\); max-width: 100%; min-width: 0;/);
  assert.match(css, /\n\.girdi-etiket > \.girdi \{ max-width: 100%; min-width: 0; \}/);
  assert.doesNotMatch(css, /\.dugme-sira > \.girdi-etiket|\.ayar-kontrol > \.girdi-etiket/, "kapsamlı kopyalar genel kurala katlandı");
  assert.match(css, /\n\.akis \.bolum > \*, \.santralim-akis \.bolum > \* \{ min-width: 0; \}/, "bölüm ızgarasındaki kart içeriğinin altına inebilir (375 px yatay taşma)");
});

// 18.11 UI denetimi Grup 3 — punto yardımcı sınıfları, kaynakta satır içi jeton puntosu kalmaz, tanım listesi kolonu içerik kadar, Mutabakat ayAd ortak biçim
test("Grup 3: .t-* sınıfları tanımlı, satır içi fontSize: var(--t-…) kalmadı, .tanim-listesi kolonu minmax(96px, max-content), ayAd → donemEtiket", async () => {
  const css = oku("../../src/index.css");
  for (const k of ["ikincil", "etiket", "govde", "kucuk", "kod", "veri", "kart", "bolum"]) assert.match(css, new RegExp(`\\n\\.t-${k} \\{ font-size: var\\(--t-${k}\\); \\}`), k);
  assert.match(css, /\.tanim-listesi li \{ display: grid; grid-template-columns: minmax\(96px, max-content\) minmax\(0, 1fr\);/);
  const fs = await import("node:fs"); const { join } = await import("node:path");
  const kok = decodeURIComponent(new URL("../../src/", import.meta.url).pathname); const dosyalar: string[] = [];
  const gez = (d: string) => { for (const a of fs.readdirSync(d)) { const y = join(d, a); if (fs.statSync(y).isDirectory()) gez(y); else if (y.endsWith(".tsx")) dosyalar.push(y); } }; gez(kok);
  const kalan = dosyalar.filter((y) => /fontSize: "var\(--t-/.test(fs.readFileSync(y, "utf8"))).map((y) => y.slice(kok.length));
  assert.deepEqual(kalan, [], "satır içi jeton puntosu yerine .t-* sınıfı");
  assert.match(oku("../../src/features/sayfalar/Mutabakat.tsx"), /const ayAd = \(d: string\) => donemEtiket\(d\);/);
});
