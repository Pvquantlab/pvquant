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
  const k = oku("../../src/shell/Kabuk.tsx"); const cl = oku("../../src/api/client.ts");
  // 18.11 gezinme (Parti C #10): fare için 90 ms bekleme + ayrılınca iptal; odak gecikmesiz; tıklama zamanlayıcıyı iptal eder
  assert.match(k, /onClick=\{\(\) => \{ isitIptal\(\); setSayfa\(s\.id\); setMenuAcik\(false\); \}\}\n\s+onMouseEnter=\{\(\) => isitPlanla\(s\.id\)\} onMouseLeave=\{isitIptal\} onFocus=\{\(\) => isit\(s\.id, plantId\)\}/);
  assert.match(k, /isitZaman\.current = window\.setTimeout\(\(\) => \{ isitZaman\.current = null; isit\(id, plantId\); \}, ISITMA_GECIKME_MS\)/);
  assert.match(cl, /export const ISITMA_GECIKME_MS = 90;/);
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
  assert.equal((s.match(/if \(!santralGorunur\) return;/g) ?? []).length, 3, "santral bölümü kapısı");   // v2.641 (02A-B10): gölge görünümü ayrı efekt (ölçüm sınırı seçilince yalnız o yeniden çekilir)
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
  // 18.11 yükleme düzeltmesi: çerçeve düz işlev (aynı <Sayfa> kökü, dört Kart yerinde kalır), gerçek satır etiketleri; hata durumu iki kademe
  assert.match(s, /if \(o === undefined\) return genelCerceve\(\);/); assert.match(s, /^function genelCerceve\(\) \{/m); assert.doesNotMatch(s, /GenelBakisIskeleti/);
  assert.match(s, /\["Beklenen üretim", "Bugüne kadar gerçekleşen", "Sapma", "Tahmin yayını", "Son ölçüm", "Ayrıntı"\]/, "ilk kartın koşulsuz satır etiketleri");
  assert.match(s, /<KunyeIskeleti etiketler=\{ISKELET_SATIR\[k\]\} notSatir=\{2\} \/>/); assert.match(s, /<div className="bos-durum" role="alert"><div className="bos-bas">Genel bakış sunucudan alınamadı<\/div>/);
  assert.match(s, /const KART_BASLIKLARI = \["Bugün ne kadar üretim bekleniyor\?", "Yarının üretim programı hazır mı\?", "Açık veri ve operasyon riskleri", "Finansal durum nedir\?"\] as const;/);
  assert.equal((s.match(/baslik=\{KART_BASLIKLARI\[\d\]\}/g) ?? []).length, 4, "dört kart ortak sabitten"); assert.match(s, /const ISKELET_SATIR: readonly \(readonly \(string \| null\)\[\]\)\[\] = \[/);
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
  assert.match(efekt, /setRv\(bellekten\.kgupRevizyon\(plantId\)\);/, "santral geçişinde bellekteki anında");
  // 19.11 Bulgu 2: önizleme efekti santral × seviye; seviye değişiminde eski değer bekler, santral değişiminde iskelet
  assert.match(s, /const bellek = bellekten\.kgup\(plantId, kgupKantil\);\n\s+if \(bellek \|\| santralDegisti\) setKgup\(bellek\);/, "seviye değişiminde eski değer solgun bekler");
  assert.match(s, /api\.kgupOnizleme\(plantId, undefined, kgupKantil\)/, "önizleme seçili seviyeyle istenir");
  assert.match(s, /\}, \[plantId, ds, kgupKantil\]\);/, "seviye bağımlılıkta");
  assert.match(s, /aria-busy=\{kgupBekliyor \|\| undefined\}/, "yoldayken aria-busy");
  assert.equal((s.match(/disabled=\{kgupBekliyor\}/g) ?? []).length, 2, "yoldayken KGÜP ve EAK indirmesi kilitli (ekran eski seviye, dosya yeni seviye olmasın)");
  assert.match(s, /\(santralDegisti \|\| e === undefined\) \? v : e/, "seviye değişiminde null yanıt eski değeri silmez (seçici sökülmez)");
  assert.doesNotMatch(s, /api\.kgupOnizleme\(plantId\)[^,]/, "p50'ye sabit önizleme çağrısı kalmadı");
  assert.match(s, /setKgup\(\(e\) => \(v \? ayniysaEskisi\(e, v\) : /, "aynı veri yeniden çizdirmez");   // 19.11: önizleme ikinci efekte taşındı; null dalı inceleme pini
  assert.match(s, /onToggle=\{\(e\) => \{ if \(\(e\.currentTarget as HTMLDetailsElement\)\.open && surumler === undefined\) surumleriYenile\(\); \}\}/, "açılınca istenir");
  assert.match(s, /<div className="akis">/); assert.equal((s.match(/<section className="bolum">/g) ?? []).length, 2, "Yarın / Bugün bölümleri");
  assert.match(s, /<div className="ozet-bas">Yarın<span className="sag">/); assert.match(s, /<div className="ozet-bas">Bugün<span className="sag">/);
  assert.doesNotMatch(s, /baslik="Üretim programı \(KGÜP\) —/, "kart başlığı sayfa başlığını yinelemez");
  assert.match(s, /kgup === undefined \? \([\s\S]{0,220}<ProgramIskeleti \/>/); assert.match(s, /rv === undefined \? <RevizyonIskeleti \/>/);
  assert.match(s, /function ProgramIskeleti\(\)[\s\S]*?className="program-ozet"[\s\S]*?className="dugme-grubu"/, "iskelet gerçek kalıpta");
  assert.match(s, /Array\.from\(\{ length: 13 \}/, "revizyon iskeleti 13 satır (gün ortası)");
  const cl = oku("../../src/api/client.ts");
  assert.match(cl, /kgup: \(p: string, kantil = "p50"\): KgupOnizleme \| undefined => bellektenOku<KgupOnizleme>\(`\/v1\/plants\/\$\{p\}\/kgup\?fmt=json&kantil=\$\{kantil\}`\)/, "bellek yolu kgupOnizleme ile birebir (19.11: seviye parametreli)");
  assert.match(cl, /kgupRevizyon: \(p: string\): KgupRevizyon \| undefined => bellektenOku<KgupRevizyon>\(`\/v1\/plants\/\$\{p\}\/kgup\/revizyon`\)/);
  // 19.11 Bulgu 4: iş gereği «kayıt yok» 200 + {yok:true} → bellek ve ağ okuyucuları null'a çevirir (sayfalar değişmedi)
  assert.match(cl, /export function yokIseNull<T>\(v: T \| undefined\): T \| null \| undefined \{ return v && \(v as \{ yok\?: boolean \}\)\.yok === true \? null : v; \}/);
  assert.equal((cl.match(/yokIseNull\(/g) ?? []).length, 4, "kalibrasyon/kayıp ağacı bellek ve ağ (4 kullanım; tanım yokIseNull<T>)");
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
  // 18.11 yükleme düzeltmesi: çerçeve içerikle aynı kök ve çocuk konumları (ModulNotu + .akis), hedef gün düğmeleri aynı öğe; kart içi yer tutucular yapılı
  assert.match(s, /if \(liste === undefined\) return <Sayfa baslik="Portföy yönetimi" alt=\{alt\} sag=\{secici\}><ModulNotu kod="portfoy_dsg" \/>\{portfoylerCercevesi\(hedefSeg\)\}<\/Sayfa>;/);
  assert.doesNotMatch(s, /PortfoylerIskeleti|<YerTutucu yukseklik=\{(120|140|80)\} \/>/); assert.equal((s.match(/sag=\{hedefSeg\}/g) ?? []).length, 2);
  assert.match(s, /sapma === undefined \? <TabloIskeleti sutunlar=\{KATKI_SUTUN\} satir=\{3\} \/>/); assert.match(s, /fin === undefined \? <TabloIskeleti sutunlar=\{FIN_SUTUN\} satir=\{5\} dar \/>/);
  assert.match(s, /const KATKI_SUTUN: readonly IskeletSutun\[\] = \[\{ ad: "Santral", sol: true, tur: "metin" \}, \{ ad: "Kurulu güç \(kW\)" \}, \{ ad: "Program \(MWh\)" \}, \{ ad: "Gerçekleşen \(MWh\)" \}, \{ ad: "Sapma \(MWh\)" \}/);
  assert.equal((s.match(/<section className="bolum">/g) ?? []).length, 4 + 3, "4 bölüm + çerçevede 3 (Kayıtlar seçili portföyü ister)");
  for (const b of ["Dönem", "Önümüzdeki günler", "Üyelik ve finans", "Kayıtlar"]) assert.match(s, new RegExp(`<div className="ozet-bas">${b}<span className="sag">`), b);
  assert.doesNotMatch(s, /ızgara-cift/, "çiftler .sira-2 (Santralim ile aynı)"); assert.equal((s.match(/<div className="sira-2">/g) ?? []).length, 2 + 2, "sayfa 2 + çerçeve 2");
  const cl = oku("../../src/api/client.ts");
  assert.match(cl, /sapma\?ozet=1\$\{donem \? `&donem=/, "sapma ozet=1 (saatlik liste gelmez)");
  assert.match(cl, /portfoySapma: \(id: string, donem\?: string \| null\): PortfoySapmaT \| undefined => bellektenOku<PortfoySapmaT>\(`\/v1\/portfoyler\/\$\{id\}\/sapma\?ozet=1/, "bellek yolu api ile birebir");
  assert.match(cl, /portfoyler: \(\) => \{ const pf = localStorage\.getItem\("pvq_portfoy"\);/, "ısıtma hatırlanan portföyün açılış uçlarını kapsar");
  const css = oku("../../src/index.css");
  assert.match(css, /\.akis \.bolum \{ container-type: inline-size; \}/);
  assert.match(css, /@container \(min-width: 700px\) and \(max-width: 1000px\) \{ \.akis \.satir-4 \{ grid-template-columns: repeat\(2, minmax\(0, 1fr\)\); \} \}/);
});

// 18.11 UI denetimi Grup 1 — Doğruluk: altı yanıt bayat-önce, iki görünürlük kapısı, beş bölümlü akış, sayfaya özel iskelet
test("Doğruluk: bayat-önce altı okuyucu, güvenilirlik ve uzlaştırma kapılı, .akis bölümleri, yükleme çerçevesi", () => {
  const s = oku("../../src/features/sayfalar/Dogruluk.tsx");
  for (const [ad, n] of [["hataDagilimi(plantId)", 2], ["konformal(plantId)", 2], ["backtest(plantId)", 3], ["dengesizlik(plantId)", 3], ["guvenilirlik(plantId)", 3], ["yekdem(plantId)", 2]] as const) assert.equal((s.split(`bellekten.${ad}`).length - 1), n, `${ad}: başlangıç + ana efekt (+ kapılı efekt)`);
  assert.match(s, /useState<BagimsizDogrulama \| null \| undefined>\(\(\) => bellekten\.bagimsizDogrulama\(plantId, donem, bdKural\)\)/);
  assert.match(s, /const \[ortaRef, ortaGorunur\] = useGorunur<HTMLElement>\(\);/);
  assert.match(s, /setBd\(bellekten\.bagimsizDogrulama\(plantId, donem, bdKural\)\)/);
  assert.match(s, /const \[altRef, altGorunur\] = useGorunur<HTMLElement>\(\);/);
  assert.match(s, /if \(!ortaGorunur\) return;[\s\S]{0,160}api\.guvenilirlik\(plantId\)[\s\S]{0,200}api\.backtest\(plantId\)/, "güvenilirlik ve geri test (Parti C #6) yalnız kart görünür olunca");
  assert.match(s, /if \(!altGorunur\) return;[\s\S]{0,200}api\.dengesizlik\(plantId\)/, "uzlaştırma yalnız görünür olunca");
  // 18.11 Parti 3: hata dağılımı açılışta (üst KPI'ı besler), YEKDEM açılışta ve kart segmenti yanıttan (dz'yi beklemez, araya girmez); yer tutucular gerçek boyda
  assert.doesNotMatch(s.slice(s.indexOf("if (!altGorunur) return;"), s.indexOf("}, [plantId, ds, altGorunur]);")), /api\.hataDagilimi\(/, "dağılım kapıda değil");
  assert.match(s, /api\.hataDagilimi\(plantId\)\.then[\s\S]{0,160}api\.yekdem\(plantId\)\.then\(\(v\) => \{ if \(acik\) setYk\(v\); \}\);\n    return \(\) => \{ acik = false; \};/, "ana efekt: hata dağılımı + yekdem");
  // 18.11 yükleme düzeltmesi: dönem seçicisi, bağımsız doğrulama ve YEKDEM kartı çerçeve ve içerikte aynı öğe; aynı <Sayfa> kökü
  assert.match(s, /const yekdemKarti = \(yk === undefined \|\| yk\?\.uygulanir\) \? <YekdemKarti yk=\{yk\} \/> : null;/); assert.equal((s.match(/\{yekdemKarti\}/g) ?? []).length, 2);
  assert.equal((s.match(/\{bagimsizKarti\}/g) ?? []).length, 2); assert.equal((s.match(/\{donemSeg\}/g) ?? []).length, 2);
  assert.match(s, /if \(!hazir\) return dogrulukCercevesi\(donemSeg, bagimsizKarti, yekdemKarti\);/); assert.doesNotMatch(s, /DogrulukIskeleti/);
  assert.match(s, /function YekdemKarti\(\{ yk \}: \{ yk: Yekdem \| null \| undefined \}\)/);
  assert.doesNotMatch(s, /api\.yekdem\(plantId, gun\)/, "YEKDEM kartı kendi istek atmaz");
  for (const [sabit, ad] of [["BD_ISK", "bağımsız doğrulama"], ["DZ_ISK", "uzlaştırma"], ["YK_ISK", "YEKDEM"], ["HD_ISK", "dağılım"], ["GV_ISK", "güvenilirlik"]] as const) assert.ok(s.includes(`=== undefined ? ${sabit} :`) || s.includes(`=== undefined && <div style={{ marginTop: 14 }}>{${sabit}}</div>`), `${ad} yapılı iskeleti ${sabit}`);
  assert.doesNotMatch(s, /<YerTutucu yukseklik=/, "tek gri blok kalmadı"); assert.match(s, /<KpiIskeleti etiket="Fiyat rejimi" \/>/); assert.match(s, /\["Program doğruluğu", "bir gün önce 15:30 kesimi öncesi son tahmin", \["WMAPE", "Gün"\]\]/);
  assert.match(oku("../../src/api/client.ts"), /yekdem: \(p: string, gun = 90\): Yekdem \| undefined => bellektenOku<Yekdem>\(`\/v1\/plants\/\$\{p\}\/yekdem\?gun=\$\{gun\}`\)/);
  const ana = s.slice(s.indexOf("api.karne(plantId, donem).then((v) => { if (acik)"), s.indexOf("}, [plantId, ds]);"));
  assert.doesNotMatch(ana, /api\.(guvenilirlik|dengesizlik|backtest)\(/, "ana efekt: karne, konformal, hata dağılımı, yekdem (güvenilirlik/uzlaştırma/geri test kapıda)");
  assert.doesNotMatch(s, /SayfaIskeleti/);
  assert.equal((s.match(/<section className="bolum"/g) ?? []).length, 5 + 5, "5 bölüm + çerçevede 5 (aynı yapı)");
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
  assert.match(s, /if \(!hazir\) return aylikCerceve\(\);/); assert.doesNotMatch(s, /AylikIskeleti|<YerTutucu yukseklik=/);   // 18.11 yükleme düzeltmesi: düz işlev, aynı kök; yapılı iskeletler
  assert.equal((s.match(/<section className="bolum">/g) ?? []).length, 4 + 4, "4 bölüm + çerçevede 4 (aynı yapı)");
  assert.equal((s.match(/alt=\{PD_ALT\}/g) ?? []).length, 2); assert.equal((s.match(/alt=\{PF_ALT\}/g) ?? []).length, 2); assert.equal((s.match(/\{BANKABLE_ISK\}|\? BANKABLE_ISK/g) ?? []).length, 2, "yıllık kart iskeleti sayfa + çerçeve");
  for (const b of ["Bu ay ve yıl", "Yıl yıl ve performans", "İklim arşivi", "Gerçekleşen"]) assert.match(s, new RegExp(`<div className="ozet-bas">${b}<span className="sag">`), b);
  const cl = oku("../../src/api/client.ts");
  assert.match(cl, /performans: \(p: string, ay = 12\): Performans \| undefined => bellektenOku<Performans>\(`\/v1\/plants\/\$\{p\}\/performans\?ay=\$\{ay\}`\)/);
});

// 18.11 UI denetimi Grup 1 — Kalibrasyon: altı teşhis yanıtı bayat-önce, dört bölümlü akış, sayfaya özel iskelet, başlık yinelemesi yok
test("Kalibrasyon: hijyen/kayma/kayıp ağacı/güç matrisi/saat profili/kayıp ayrışımı bayat-önce, .akis dört bölüm, KalibrasyonIskeleti", () => {
  const s = oku("../../src/features/sayfalar/Digerleri.tsx");
  const K = s.slice(s.indexOf("export function Kalibrasyon("), s.indexOf("const KATSAYI_ETIKET = "));
  for (const ad of ["hijyen(plantId)", "kayma(plantId)", "kayipAgaci(plantId)", "gucMatrisi(plantId)", "saatProfili(plantId)", "kayipAyrisimi(plantId)"]) assert.equal((K.split(`bellekten.${ad}`).length - 1), 2, `${ad}: başlangıç + efekt`);
  assert.doesNotMatch(K, /setHj\(undefined\)|setKy\(undefined\)|setSp\(undefined\)/, "santral geçişinde yer tutucuya düşmez");
  assert.match(K, /if \(!yuklendi\) return kalibrasyonCercevesi\(<KayipAgaciKarti plantId=\{plantId\} ilkVeri=\{ka\} \/>, <GucMatrisiKarti plantId=\{plantId\} ilkVeri=\{gm\} \/>\);/);   // 18.11 yükleme düzeltmesi
  assert.doesNotMatch(K, /<YerTutucu yukseklik=/, "Kalibrasyon'da tek gri blok kalmadı"); assert.match(s, /const KATSAYI_ETIKET = \["Sistem verim katsayısı", "Çift yüzlü panel kazancı", "Geçerli saat"/);
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
test("Finansal etki: bayat-önce (program ve senaryo yolu), .akis dört bölüm, yükleme çerçevesi gerçek başlıklarla (Parti 2)", () => {
  const s = oku("../../src/features/sayfalar/FinansalEtki.tsx");
  assert.match(s, /const bellektekiSonuc = \(plantId: string, kod: string, uretim: string \| null, pozisyon: "program" \| "uretim"\) =>\n  pozisyon === "program" \? bellekten\.finansalEtki\(plantId, kod, uretim\) : bellekten\.finansalEtkiSenaryo\(plantId, kod, pozisyon, null, uretim\);/);
  assert.equal((s.split("bellektekiSonuc(plantId, kod, uretim, pozisyon)").length - 1), 2, "başlangıç + efekt (bileşen dışı saf yardımcı; efekt bağımlılığı yok)");
  assert.doesNotMatch(s, /setO\(undefined\)/, "geçişte iskelete düşmez"); assert.match(s, /setO\(\(e\) => e \?\? null\)/, "tazeleme düşerse bellekteki kalır");
  // 18.11 yükleme düzeltmesi: tek <Sayfa> kökü — çerçeve / hata / içerik aynı konumda (seçiciler ve kartlar yeniden takılmaz; odak düşmez)
  assert.equal((s.match(/<Sayfa baslik="Finansal etki"/g) ?? []).length, 1, "tek Sayfa kökü");
  assert.match(s, /\{o === undefined \? cerceve\(kod, gecmisDetay\) : o === null \? <FinansalEtkiHata kodu=\{hataKodu\} \/> : icerik\(o, plantId, gecmisDetay\)\}/);
  assert.doesNotMatch(s, /FinansalEtkiCerceve|SayfaIskeleti|ızgara-cift|iskelet-kpi|iskelet-kart/);
  assert.match(s, /^function icerik\(o: FinansalEtkiT, plantId: string, gecmisDetay: React\.ReactNode\) \{/m, "içerik düz işlev (bileşen değil): öğe türleri çerçeveyle aynı");
  assert.match(s, /^function cerceve\(kod: string, gecmisDetay: React\.ReactNode\) \{/m);
  assert.equal((s.match(/\{gecmisDetay\}/g) ?? []).length, 2, "kayıtlı sürümler alanı iki durumda aynı öğe"); assert.equal((s.match(/\{NASIL_DETAY\}/g) ?? []).length, 2);
  // yapılı iskelet: bileşen tablosu gerçek başlık satırı (BILESEN_BASLIK sayfa + çerçeve), 3 toplanan + Toplam + grup + 4 toplanmayan satır; künyeler koşulsuz etiketlerle
  assert.equal((s.match(/\{BILESEN_BASLIK\}/g) ?? []).length, 2, "başlık satırı tek kaynaktan");
  assert.match(s, /\{\[0, 1, 2\]\.map\(\(i\) => <IskeletSatir key=\{i\} sutunlar=\{BILESEN_SUTUN\} notlu \/>\)\}\s*<tr style=\{\{ fontWeight: 600 \}\}><td style=\{sol\}>Toplam<\/td>/);
  assert.match(s, /Toplama girmeyen satırlar<\/td><\/tr>\s*\{\[0, 1, 2, 3, 4\]\.map\(\(i\) => <IskeletSatir key=\{i\} sutunlar=\{BILESEN_SUTUN\} notlu \/>\)\}/);
  assert.match(s, /<KunyeIskeleti etiketler=\{HESAP_ETIKET\} \/>/); assert.match(s, /<KunyeIskeleti etiketler=\{DUSUKLUK_ETIKET\} \/>/);
  assert.match(s, /const HESAP_ETIKET = \["Dönem", "Hesap durumu", "Üretim girdisi", "Program", "Fiyat", "Uzlaştırma kuralı", "Satış tarifesi", "Piyasa pozisyonu", "Hesap sözlüğü"\] as const;/, "yalnız koşulsuz künye satırları");
  assert.doesNotMatch(s, /<YerTutucu yukseklik=\{(900|120|300|600|350|820)\} \/>/, "tek gri blok kalmadı");
  assert.equal((s.match(/<KpiIskeleti [^>]*ikinci \/>/g) ?? []).length, 2, "ikinci değer satırı olan iki KPI");
  // hata türü ayrımı: geçersiz dönem / sunucu / ağ; bellekte sonuç varsa hata görünmez
  assert.match(s, /\(h: unknown\) => \{ if \(acik\) \{ setO\(\(e\) => e \?\? null\); setHataKodu\(hataKoduOku\(h\)\); \} \}/);
  assert.match(s, /const gecersiz = kodu === "400" \|\| kodu === "404" \|\| kodu === "422";/);
  const pr = oku("../../src/features/sayfalar/parcalar.tsx");
  for (const ad of ["IskeletHucre", "IskeletSatir", "TabloIskeleti", "KunyeIskeleti", "ListeIskeleti", "MetinIskeleti", "SatirlarIskeleti"]) assert.match(pr, new RegExp(`export function ${ad}\\(`), ad);
  assert.match(pr, /<table className=\{`veri sayisal iskelet-tablo\$\{dar \? " dar" : ""\}`\} aria-hidden="true">/, "iskelet tablosu ekran okuyucuya kapalı");
  const css = oku("../../src/index.css");
  assert.match(css, /\.iskelet-cubuk \{ display: inline-block; height: 14px; border-radius: 4px; vertical-align: middle; max-width: 100%; \}/);
  assert.match(css, /table\.veri\.iskelet-tablo tbody tr:hover td \{ background: transparent; \}/);
  assert.doesNotMatch(css, /iskelet[^{]*\{[^}]*animation/, "iskelet hareketsiz");
  // sayfa geçişinde kaydırma başa (ÖLÇÜLDÜ: Genel bakış 401 px kaydırılmışken Finansal etki 401 px'te açılıyordu)
  const app = oku("../../src/App.tsx");
  assert.match(app, /const sayfaSec = useCallback\(\(s: SayfaId\) => \{\n    if \(yeniSurumVar\(\)\) \{[\s\S]{0,700}?\n    \}\n/);   // 19.11 Bulgu 7: sürüm kayması kapısı başa
  assert.match(app, /useLayoutEffect\(\(\) => \{ window\.scrollTo\(0, 0\); \}, \[sayfa, bekleyen\]\);/);   // G2 O-2 (21.11): kaydırma yeni içerik/iskeletle aynı karede (sayfaSec'te eşzamanlı değil)
  assert.equal((s.match(/<section className="bolum">/g) ?? []).length, 4 + 4, "4 bölüm + çerçevede 4 (aynı yapı)");
  // 18.11 Parti 2: çerçeve gerçek yapıyı taşır — kart başlık/açıklamaları KART sabitinden (sayfa 6 + çerçeve 6), dört KPI etiketi bilgiyle, gövdeler boyutlu yer tutucu
  assert.equal((s.match(/baslik=\{KART\.\w+\.baslik\} alt=\{KART\.\w+\.alt\}/g) ?? []).length, 12, "6 kart × (sayfa + çerçeve)");
  assert.equal((s.match(/<KpiIskeleti /g) ?? []).length, 4); assert.doesNotMatch(s, /KpiYerTutucu/, "KPI iskeleti ortak (parcalar)");
  assert.match(s, /const donem = donemEtiket\(kod\);[\s\S]{0,400}<div className="ozet-bas">Dönem<span className="sag">\{donem\}<\/span><\/div>/, "çerçeve dönem etiketi gerçek");
  assert.match(s, /\{!gecmisAcik \? null : gecmis === undefined \? <YerTutucu yukseklik=\{48\} \/>/, "kapalı details içinde yer tutucu yok");
  assert.doesNotMatch(s, /role="status"[^>]*>\s*<section className="bolum">\s*<div className="ozet-bas">Dönem<span className="sag">yükleniyor…/, "eski gri iskelet kalmadı");
  for (const b of ["Dönem", "Karşılaştırma ve eylem", "Düşüklük ve ileriye", "Hesap"]) assert.match(s, new RegExp(`<div className="ozet-bas">${b}<span className="sag">`), b);
  assert.equal((s.match(/alt=\{SAYFA_ALT\}/g) ?? []).length, 1, "tek Sayfa kökü: açıklama bir kez");
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

test("Gezinme Parti A: soğuk parçada hedef başlıklı iskelet aynı karede, ECharts tembel ve kritik yol dışında, ön yükleme listesi tüm sayfalar, Tahminler/Paylaşım başlıklı iskelet", async () => {
  const app = oku("../../src/App.tsx");
  // #1 geçiş iskeleti: tüm sayfa parçaları tembel() (hazirMi); soğuksa iskelet + parça inince geçiş, sıra koruması seciliRef
  assert.match(app, /hazirMi: \(\) => hazir !== null/);
  assert.match(app, /const \[bekleyen, setBekleyen\] = useState<SayfaId \| null>\(null\);/);
  assert.match(app, /\{bekleyen \? <GecisIskeleti sayfa=\{bekleyen\} santralAd=\{santralAd\} \/> : <Suspense fallback=\{null\}>/);
  assert.match(app, /else \{ setBekleyen\(s\); PARCALAR\[s\]\.onYukle\(\)\.catch\(\(\) => \{\}\)\.then\(\(\) => \{ if \(seciliRef\.current === s\) gec\(\); \}\); \}/, "soğuk: iskelet acil, sayfa parça inince; sıra koruması");
  assert.match(app, /const gec = \(\) => startTransition\(\(\) => \{ setSayfa\(s\); setBekleyen\(null\); \}\);/, "iskelet sayfayla aynı geçişte kalkar");
  assert.match(app, /const ad = sayfa === "santralim" \? santralAd : GECIS_BASLIK\[sayfa\] \?\? SAYFALAR\.find/);
  // geçiş iskeletinin başlığı sayfanın gerçek h1'i ile aynı (yan menü adından farklı olanlar haritada; harita sayfa dosyasıyla uyumlu)
  const harita = /const GECIS_BASLIK[^\n]*= \{([^}]*)\}/.exec(app)![1];
  const DOSYA: Record<string, string> = { dogruluk: "Dogruluk.tsx", kgup: "Kgup.tsx", portfoyler: "Portfoyler.tsx" };
  const girdiler = [...harita.matchAll(/(\w+): "([^"]+)"/g)];
  assert.equal(girdiler.length, 3);
  for (const [, id, baslik] of girdiler) assert.ok(oku(`../../src/features/sayfalar/${DOSYA[id]}`).includes(`baslik="${baslik}"`), `${id}: sayfa h1 «${baslik}» değil`);
  assert.match(app, /setSecili\(s\); seciliRef\.current = s;/);
  assert.match(app, /if \(h\.sayfa && h\.sayfa !== sayfa\) sayfaSec\(h\.sayfa\);/, "hash yolu da aynı geçiş");
  assert.doesNotMatch(app, /lazy\(\(\) => import\("\.\/features\/(sayfalar|santralim|genel)\//, "sayfa parçaları lazy değil tembel (eşzamanlı çizim + hazirMi)");
  // #8 ön yükleme: her tembel sayfa bileşeni PARCALAR'da; liste yan menü sırasıyla + ECharts
  const tembeller = [...app.matchAll(/const (\w+) = tembel\(\(\) => import\("\.\/features\//g)].map((m) => m[1]).filter((a) => a !== "Kabuk");
  const parcalar = app.slice(app.indexOf("const PARCALAR"), app.indexOf("const ONYUKLENECEKLER"));
  assert.ok(tembeller.length >= 18, "tembel sayfa bileşenleri bulunmalı: " + tembeller.length);
  for (const a of tembeller) assert.match(parcalar, new RegExp(`\\b${a}\\b`), `${a} ön yükleme haritasında değil`);
  assert.match(app, /Santralim\.onYukle, \(\) => import\("\.\/lib\/echarts"\),\n  \.\.\.GRUPLAR\.flatMap\(\(g\) => g\.sayfalar\)/);
  // #2 ECharts tembel: değer içe aktarması yalnız echartsYukle.ts'te dinamik; EChart ve kahraman grafik type-only + yükleyici
  const kaynak = (await import("node:fs")).readFileSync;
  const kok = new URL("../../src/", import.meta.url);
  const yukleyici = kaynak(new URL("lib/echartsYukle.ts", kok), "utf8");
  assert.match(yukleyici, /import type \* as E from "\.\/echarts";/);
  assert.match(yukleyici, /soz \?\?= import\("\.\/echarts"\)/);
  for (const yol of ["lib/EChart.tsx", "features/sayfalar/ProductionForecastChart.tsx"]) {
    const k = kaynak(new URL(yol, kok), "utf8");
    assert.match(k, /import type \* as echarts from "[./]*lib\/echarts"|import type \* as echarts from "\.\/echarts"/, `${yol}: yalnız tür`);
    assert.doesNotMatch(k, /^import \* as echarts from/m, `${yol}: statik değer içe aktarması kritik yola ECharts koyar`);
    assert.match(k, /echartsYukle\(\)\.then\(\(m\) => \{ if \(acik\) setKut\(m\); \}/, `${yol}: yükleyici`);
    assert.match(k, /kut\.init\(/, `${yol}: init inmiş modülden`);
  }
  const fs = await import("node:fs"); const path = await import("node:path"); const { fileURLToPath } = await import("node:url");
  const gez = (d: string): string[] => fs.readdirSync(d).flatMap((a) => { const y = path.join(d, a); return fs.statSync(y).isDirectory() ? gez(y) : /\.tsx?$/.test(a) ? [y] : []; });
  const statik = gez(fileURLToPath(kok)).filter((y) => !/lib\/echartsYukle\.ts$/.test(y) && /^import \* as \w+ from "[./]*lib\/echarts"|^import \* as \w+ from "\.\/echarts"|^import \{[^}]*\} from "[./]*(lib\/)?echarts"/m.test(fs.readFileSync(y, "utf8")));
  assert.deepEqual(statik, [], "lib/echarts'ı statik içe aktaran dosya kalmamalı");
  // #7 Tahminler/Paylaşım: iskelet gerçek başlıkla
  assert.match(oku("../../src/features/sayfalar/Tahminler.tsx"), /if \(!hazir\) return <Sayfa baslik="Tahminler" alt="[^"]+"><SayfaIskeleti kpi=\{0\} kart=\{2\} bas=\{false\} \/><\/Sayfa>;/);
  assert.match(oku("../../src/features/sayfalar/Paylasim.tsx"), /if \(liste === null\) return <Sayfa baslik="Paylaşım" alt=\{PAYLASIM_ALT\}><SayfaIskeleti kpi=\{0\} kart=\{1\} bas=\{false\} \/><\/Sayfa>;/);
  assert.match(oku("../../src/features/sayfalar/parcalar.tsx"), /\{bas && <div className="iskelet-bas">/);
});

test("Hakkında (Parti 4): dört kart koşulsuz, gövdeler yer tutuculu, veri yok/alınamadı açık", () => {
  const s = oku("../../src/features/sayfalar/Hakkinda.tsx");
  for (const b of ["Veri kaynakları ve lisanslar", "Mevzuat ve standart dayanağı", "Uzlaştırma kuralı sürüm tablosu", "Meteoroloji arşivi"]) assert.match(s, new RegExp(`\\n {6,8}<Kart baslik="${b}"`), b);
  assert.doesNotMatch(s, /\{h && \(h\.mevzuat|\{kurallar && kurallar\.satirlar\.length > 0 && \(|\{h && Object\.keys\(h\.arsiv\)/, "kart koşulsuz (veri gelince araya girmez)");
  for (const h of [490, 680, 560, 180]) assert.ok(s.includes(`<YerTutucu yukseklik={${h}} />`), `yer tutucu ${h}`);
  assert.match(s, /kurallar\?\.satirlar\.some\(\(r\) => r\.dogrulama === "dogrulama_gerekli"\)/);
  assert.equal((s.match(/\bALINAMADI\b/g) ?? []).length, 5, "tek dürüst metin: tanım + dört kart"); assert.equal((s.match(/"Kayıt yok\."/g) ?? []).length, 2); assert.match(s, /"Arşiv boş\."/);
});


// 18.11 canlı teşhis — sunucu bayat-önce: X-Bayat yanıtı kullanılır, Kabuk «güncelleniyor» yazar, yol tek-uçuş yeniden istenir, tazesi gelince damgaYay()
test("İstemci bayat-önce: X-Bayat işlenir, geri çekilmeli yeniden isteme, çıkışta temizlik, Kabuk çipi", () => {
  const cl = oku("../../src/api/client.ts");
  assert.match(cl, /bayatIsle\(yol, y\.headers\.get\("x-bayat"\) === "1"\);/, "her getir yanıtı bayrağı işler");
  assert.match(cl, /const BAYAT_BEKLEME_SN = \[4, 6, 10, 20, 30\] as const;/);
  assert.match(cl, /if \(bayatlar\.delete\(yol\)\) \{ bayatYay\(\); damgaYay\(\); \}/, "taze gelince açık sayfa yenilenir");
  assert.match(cl, /if \(bayatZamanlayici\.has\(yol\)\) return;/, "sayfanın kendi isteği ikinci plan açmaz"); assert.match(cl, /bayatZamanlayici\.set\(yol, window\.setTimeout\(\(\) => \{\n    bayatZamanlayici\.delete\(yol\);/);
  assert.match(cl, /export function bayatSayisi\(\): number/); assert.match(cl, /export function bayatDinle\(d: \(\) => void\): \(\) => void/);
  assert.match(cl, /export function cikis\(\): void \{\n  bayatlar\.clear\(\); bayatYay\(\);/, "çıkışta bekleyen yenilemeler düşer");
  assert.match(cl, /import \{ damgaYay \} from "\.\.\/shell\/damgaOlay";/);
  const kb = oku("../../src/shell/Kabuk.tsx");
  assert.match(kb, /const \[bayat, setBayat\] = useState\(bayatSayisi\(\)\);/); assert.match(kb, /useEffect\(\(\) => bayatDinle\(\(\) => setBayat\(bayatSayisi\(\)\)\), \[\]\);/);
  assert.match(kb, /bayat > 0 && "güncelleniyor",/, "çip yalnız bayat yanıt beklerken");
});

test("19.11 Bulgu 7: sürüm kayması — X-PVQ-Yazilim ilk görülenle kıyaslanır, sonraki sayfa geçişi bir kez yeniden yükler, Kabuk çipi", () => {
  const cl = oku("../../src/api/client.ts");
  assert.match(cl, /export function surumIsle\(s: string \| null\): void \{\n  if \(!s\) return;\n  if \(ilkSurum === null\) \{ ilkSurum = s; return; \}\n  if \(s !== ilkSurum && !yeniSurum\) \{ yeniSurum = true;/);
  assert.equal((cl.match(/surumIsle\(y\.headers\.get\("x-pvq-yazilim"\)\)/g) ?? []).length, 3, "getir + gonder + damga yoklaması (boşta duran sekme)");
  assert.doesNotMatch(cl, /headers\.get\("x-pvq-surum"\)/, "X-PVQ-Surum KGÜP arşiv sürümüdür, kayma kıyasında kullanılmaz");
  const app = oku("../../src/App.tsx");
  assert.match(app, /const sayfaSec = useCallback\(\(s: SayfaId\) => \{\n    if \(yeniSurumVar\(\)\) \{[\s\S]{0,700}history\.replaceState\(history\.state, "", `#\$\{s\}[\s\S]{0,80}?\); window\.location\.reload\(\); return;/, "sayfa geçişinde tek sefer yeniden yükleme; hashchange üretmeden");
  const kb = oku("../../src/shell/Kabuk.tsx");
  assert.match(kb, /yeniSurum && "yeni sürüm yayında; sonraki sayfa geçişinde yenilenir"/);
  assert.match(kb, /useEffect\(\(\) => surumDinle\(\(\) => setYeniSurum\(true\)\), \[\]\);/);
  const yn = oku("../../src/api/yonetim.ts"); assert.match(yn, /surumIsle\(y\.headers\.get\("x-pvq-yazilim"\)\)/, "yönetim istemcisi de başlığı besler");
  const pk = oku("../../src/features/yonetim/PlatformKabugu.tsx"); assert.match(pk, /if \(yeniSurumVar\(\)\) \{ window\.location\.reload\(\); return; \} setSayfa\(s\.id\);/, "platform kabuğu geçişte yeniden yükler");
  assert.match(cl, /function kanal\(\) \{ const d = new Set<\(\) => void>\(\);/, "tek dinleyici kanalı (bayat + sürüm)");
});
