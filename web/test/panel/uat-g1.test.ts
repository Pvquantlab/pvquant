// UAT 21.11.2026 (video analizi) G1 — web kaynak pinleri.
// G1-A (K-1): Santralim › Piyasa segmenti / santral türü / veri türü seçimi seçim anında YAZMAZ; yazma yalnız «Kaydet» ile.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");

test("G1-A: segment seçicisi yalnız yerel seçimi tutar, yazma Kaydet'te", () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  // onChange içinde ağ çağrısı yok
  assert.match(s, /aria-label="Piyasa segmenti"\s*\n\s*onChange=\{\(e\) => \{ setSegMesaj\(null\); setSegSecim\(e\.target\.value\); \}\}/);
  assert.doesNotMatch(s, /onChange=\{\(e\) => \{ setSegMesaj\(null\); api\.segmentAyarla\(/, "segment onChange artık yazmıyor");
  assert.doesNotMatch(s, /onChange=\{\(e\) => sinifAyarla\(/, "santral türü / veri türü onChange artık yazmıyor");
  assert.doesNotMatch(s, /const sinifAyarla = /, "seçim anında yazan yardımcı kalktı");
  // sınıf seçicileri yerel durum
  assert.match(s, /aria-label="Santral türü" onChange=\{\(e\) => \{ setSegMesaj\(null\); setSinifSecim\(\(x\) => \(\{ \.\.\.x, santral_turu: e\.target\.value \}\)\); \}\}/);
  assert.match(s, /aria-label="Veri türü" onChange=\{\(e\) => \{ setSegMesaj\(null\); setSinifSecim\(\(x\) => \(\{ \.\.\.x, veri_turu: e\.target\.value \}\)\); \}\}/);
  // Kaydet: yalnız değişen alan gider; iki uç ayrı
  // QA İ-1/İ-3: hedef santral sabitlenir, her .then plantRef'e bakar; segment Kaydet UEVÇB göndermez
  assert.match(s, /const segKaydet = \(\) => \{[\s\S]{0,200}const hedef = plantId;[\s\S]{0,200}const ayni = \(\) => plantRef\.current === hedef;[\s\S]{0,900}if \(segYeni\) zincir = zincir\.then\(\(\) => api\.segmentAyarla\(hedef, segYeni\)\.then\(\(r\) => \{ if \(!ayni\(\)\) return;[\s\S]{0,500}if \(Object\.keys\(sinifYeni\)\.length\) zincir = zincir\.then\(\(\) => api\.santralSinifiAyarla\(hedef, sinifYeni\)\.then\(\(r\) => \{ if \(!ayni\(\)\) return;/);
  assert.doesNotMatch(s.slice(s.indexOf("const segKaydet"), s.indexOf("const segKaydet") + 1600), /uevcb/, "segment Kaydet UEVÇB göndermez (İ-3)");
  // QA İ-2: uçuşta düğme pasif, çift tık yok
  assert.match(s, /const \[segYolda, setSegYolda\] = useState\(false\);/);
  assert.match(s, /const segKaydet = \(\) => \{\s*if \(segYolda\) return;/);
  assert.doesNotMatch(s.slice(s.indexOf("const segKaydet"), s.indexOf("const segKaydet") + 1200), /Promise\.all/, "tek kapı yok (gecis.test kuralı)");
  assert.match(s, /<button className="dugme" disabled=\{!segDegisti \|\| segYolda\} onClick=\{segKaydet\} aria-label="Piyasa segmenti, santral türü ve veri türünü kaydet">\{segYolda \? "Kaydediliyor…" : "Kaydet"\}<\/button>/);
  assert.match(s, /disabled=\{seg === null\} aria-label="Piyasa segmenti"/, "İ-6: seçici veri gelmeden pasif");
  assert.match(s, /<span role="status" className=\{`ayar-durum /, "İ-5: sonuç mesajı canlı bölge");
  // santral değişince seçimler düşer
  assert.match(s, /useEffect\(\(\) => \{ setSegSecim\(null\); setSinifSecim\(\{\}\); setSegMesaj\(null\); setSegYolda\(false\); \}, \[plantId\]\);/);
  // başarı/hata sınıfı DSG kalıbıyla aynı; yardım metni artık «seçim anında» demiyor
  assert.match(s, /className=\{`ayar-durum \$\{segMesaj\.startsWith\("Kaydedildi"\) \? "ok" : "hata"\}`\}>\{segMesaj\}/);
  assert.doesNotMatch(s, /seçim anında kaydedilir/);
  assert.match(s, /«Kaydet»e basınca kaydedilir/);
  // hiçbir seçici/girdi olayı doğrudan yazmaz: segmentAyarla ve santralSinifiAyarla yalnız Kaydet yollarında
  for (const satir of s.split("\n")) if (/api\.(segmentAyarla|santralSinifiAyarla)\(/.test(satir)) assert.doesNotMatch(satir, /onChange=|onBlur=/, `olay içinde yazma: ${satir.trim().slice(0, 80)}`);
});

// G1-B (Y-1): .kart-arac şeridi daralır ve sarar, en çok %60; başlık sütunu 0 px'e çökmez (ÖLÇÜLDÜ 1382 px: Doğruluk başlık 0×1003 → 390×43 px).
test("G1-B: .kart-bas > .kart-arac daralabilir, %60 sınırı, ≤900 kuralı korunur", () => {
  const css = oku("../../src/index.css");
  assert.match(css, /\.kart-bas > \.kart-arac \{ flex: 0 1 auto; min-width: 0; max-width: 60%; flex-wrap: wrap; justify-content: flex-end; \}/);
  assert.doesNotMatch(css, /\.kart-bas > \.kart-arac \{ flex: 0 0 auto; flex-wrap: nowrap; \}/, "daralmayan şerit kuralı kalktı");
  assert.match(css, /@media \(max-width: 900px\) \{\n  \.kart-bas:has\(> \.kart-arac\) \{ flex-wrap: wrap; \}\n  \.kart-bas > \.kart-arac \{ flex: 1 1 100%; max-width: none; flex-wrap: wrap; \}\n\}/);
  assert.match(css, /\.kart-baslik \{ min-width: 0; flex: 1 1 auto; \}/, "başlık esnekliği aynı");
  assert.match(css, /\.kart-bas:has\(> \.kart-arac\) > \.kart-baslik \{ flex-basis: 40%; \}/, "QA İ-1: başlık esas boyu %40, şerit yer varken daralmaz");
});

// G1-C (Y-3): hata ≠ boş durum — istemci hataya durum kodu/gerekçe iliştirir; KGÜP yalnız 409'u boş durum sayar, 422 gerekçesini gösterir;
// Aylık beklenti yalnız 404'te «birikiyor»; Santralim veri kaynakları kartı yüklenirken yer tutucu gösterir (B5-2).
test("G1-C: istemci hatası durum kodu ve gerekçe taşır; mesaj metni eski biçimde", () => {
  const c = oku("../../src/api/client.ts");
  assert.match(c, /const hata = Object\.assign\(new Error\(`\$\{y\.status\} \$\{yol\}`\), \{ durum: y\.status, detay \}\);/, "getir: durum + detay");
  assert.match(c, /throw Object\.assign\(new Error\(mesaj\), \{ durum: y\.status \}\);/, "gonder: durum");
  assert.match(c, /export function hataDurumu\(e: unknown\): number \| undefined/);
  assert.match(c, /export function hataDetayi\(e: unknown\): string \| undefined/);
  assert.match(c, /kgupOnizleme: async[\s\S]{0,400}catch \(e\) \{ if \(hataDurumu\(e\) === 409\) return null; throw e; \}/, "KGÜP: yalnız 409 boş durum");
});

test("G1-C: KGÜP 422 gerekçesi ve diğer hatalar boş durumdan ayrı; Aylık 404 ayrımı; Santralim yer tutucu", () => {
  const k = oku("../../src/features/sayfalar/Kgup.tsx");
  assert.match(k, /const \[kgupNeden, setKgupNeden\] = useState<\{ durum: number; detay\?: string \} \| null>\(null\);/);
  assert.match(k, /\(e\) => \{ if \(acik\) \{ setKgup\(\(x\) => \(\(santralDegisti \|\| x === undefined\) \? null : x\)\); setKgupNeden\(\{ durum: hataDurumu\(e\) \?\? 0, detay: hataDetayi\(e\) \}\); if \(!santralDegisti\) setKgupHata\(`Seçilen seviye için önizleme alınamadı/, "QA İ-1: seviye değişiminde hata uyarısı");
  assert.match(k, /kgupNeden \? \(kgupNeden\.durum === 422 \? "dosya üretilemedi" : "alınamadı"\) : "tahmin bekleniyor"/, "QA İ-3: çip gövdeyle tutarlı");
  assert.match(k, /<div className="bos-durum" role="status">/, "QA İ-5");
  assert.match(k, /setKgupBekliyor\(!bellek\); setKgupNeden\(null\);/, "yeni denemede neden sıfırlanır");
  assert.match(k, /kgupNeden\?\.durum === 422 \? \(<>\s*<div className="bos-bas">Yarının program dosyası üretilemedi<\/div>\s*<p>\{kgupNeden\.detay \? `\$\{kgupNeden\.detay\} ` : ""\}/);
  assert.match(k, /<div className="bos-bas">Program önizlemesi alınamadı<\/div>/);
  assert.match(k, /<div className="bos-bas">Yarın için program henüz yok<\/div>/, "409/null metni korunur");
  assert.match(k, /api\.kgupOnizleme\(plantId, undefined, kgupKantil\)/, "hiz-gezinme pini korunur");
  const a = oku("../../src/features/sayfalar/Aylik.tsx");
  assert.match(a, /const d = hataDurumu\(e\); if \(d !== 404\) setBHata\(d \? `Hata kodu \$\{d\}\.` : "Bağlantı kurulamadı\."\);/);
  assert.match(a, /const birikiyor = hazir && b === null && !bHata;/);
  assert.match(a, /<Kart baslik="Aylık beklenti alınamadı">/);
  assert.match(a, /<Kart baslik="Beklenti birikiyor">/, "404 kartı korunur");
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /const \[vyDurum, setVyDurum\] = useState<"bekliyor" \| "tamam" \| "hata">\("bekliyor"\);/);
  assert.match(s, /setVy\(null\); setVyDurum\("bekliyor"\); api\.veriYolu\(plantId\)\.then\(\(v\) => \{ if \(plantRef\.current !== plantId\) return; vyDoldur\(v\); vybDoldur\(v\); setVyDurum\(v \? "tamam" : "hata"\); \}\)\.catch\(\(\) => \{ if \(plantRef\.current === plantId\) setVyDurum\("hata"\); \}\)/);
  assert.match(s, /\{!vy && \(vyDurum === "bekliyor" \? <YerTutucu yukseklik=\{120\} \/> : <p className="soluk" style=\{\{ margin: 0 \}\} role="status">Veri kaynağı bilgisi şu anda alınamadı\.<\/p>\)\}/);
  assert.equal((s.match(/Veri kaynağı bilgisi şu anda alınamadı/g) ?? []).length, 1, "metin yalnız hata dalında");
});

// ---------------------------------------------------------------- G2 (UAT video 21.11: Y-2, Y-4, Y-6, O-1, O-2, O-3, O-8, O-10) ----------
test("G2: SCADA metni koşullu, Portföy «tahmin hazır», dar sütun tabloları tam satır, kpi-alt yok, çip tek satır", () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /\{!\(o\.saglik\?\.son_scada_iso && gunAnahtari\(Date\.parse\(o\.saglik\.son_scada_iso\), o\.tz\) === gunAnahtari\(Date\.now\(\), o\.tz\)\) && \([^\n]*\n\s*<p className="t-ikincil"[^>]*>\s*Gerçekleşen üretimi görmek için bugünün SCADA verisini yükleyin\./, "Y-2: bugün ölçüm varken metin yok (ham ISO + gunAnahtari)");
  assert.match(oku("../../src/api/client.ts"), /son_scada: trTarih\(sonScada\), son_scada_iso: sonScada \?\? null,/, "Y-2: uyarlaOzet ham ISO taşır");
  assert.match(oku("../../src/api/types.ts"), /son_scada_iso\?: string \| null;/);
  const p = oku("../../src/features/sayfalar/Portfoy.tsx");
  assert.match(p, /\$\{sayiTr\(t\.program_yukumlu\)\} tahmin hazır`/, "Y-4: sayaç «tahmin hazır»");
  assert.match(p, /pr\.hazir === true \? \["rozet-ok", "tahmin hazır"\]/, "Y-4: satır rozeti «tahmin hazır»");
  assert.doesNotMatch(p, /\["rozet-ok", "hazır"\]/);
  const t = oku("../../src/features/sayfalar/Tahminler.tsx");
  assert.doesNotMatch(t, /minmax\(0,1\.9fr\) minmax\(0,1fr\)/, "Y-6: Günlük toplamlar dar sütunda değil");
  assert.match(t, /<Kart baslik="Günlük toplamlar">/);
  const o = oku("../../src/features/sayfalar/Olaylar.tsx");
  assert.doesNotMatch(o, /className="ızgara-cift"/, "Y-6 + QA İ-2: çift ızgara kalktı; üç kart .kart-sutunu içinde (14 px aralık)");
  assert.match(o, /<div className="kart-sutunu">[^\n]*\n\s*<Kart baslik="Yeni olay"/);
  assert.match(t, /<div className="kart-sutunu">[^\n]*\n\s*<Kart\s*\n\s*baslik=\{\s*GUNLUK_MOD\[ufuk\]/, "Y-6: Tahminler grafik + günlük toplamlar .kart-sutunu (14 px aralık)");
  for (const f of ["../../src/features/sayfalar/Dogruluk.tsx", "../../src/features/sayfalar/Digerleri.tsx"]) assert.doesNotMatch(oku(f), /kpi-alt/, `O-8: ${f} kpi-alt yok`);
  assert.doesNotMatch(oku("../../src/index.css"), /\.kpi-alt/, "kpi-alt CSS'te de tanımsız kalır (kullanım yok)");
  assert.match(oku("../../src/index.css"), /@media \(min-width: 901px\) \{ \.kart-bas \.cip, \.kart-bas \.cip \.meta > \* \{ white-space: nowrap; \} \}/, "O-10: çip ≥901 px tek satır");
});

test("G2: iskelet yükseklikleri gerçek içerikle, kaydırma yeni içerikle aynı karede, 404/409/422 olumsuz bellek", () => {
  assert.match(oku("../../src/features/sayfalar/FinansalEtki.tsx"), /\{\[0, 1, 2, 3, 4\]\.map\(\(i\) => <IskeletSatir key=\{i\} sutunlar=\{BILESEN_SUTUN\} notlu \/>\)\}/, "O-1: 5 «toplama girmeyen» iskelet satırı (QA: gerçek 4–6)");
  assert.match(oku("../../src/features/sayfalar/Tahminler.tsx"), /nc === undefined \? <YerTutucu yukseklik=\{70\} \/>/, "O-1: 6 saat kartı iskeleti 70 px");
  assert.match(oku("../../src/features/sayfalar/Digerleri.tsx"), /<Kart baslik="Zamanlanmış gönderim"><YerTutucu yukseklik=\{250\} \/><\/Kart>/, "O-1: zamanlanmış gönderim iskeleti 250 px");
  const a = oku("../../src/App.tsx");
  assert.match(a, /useLayoutEffect\(\(\) => \{ window\.scrollTo\(0, 0\); \}, \[sayfa, bekleyen\]\);/, "O-2: kaydırma yeni içerik/iskeletle aynı karede");
  const sec = a.slice(a.indexOf("const sayfaSec = useCallback"), a.indexOf("}, []);", a.indexOf("const sayfaSec = useCallback")));
  assert.match(sec, /if \(s === seciliRef\.current\) window\.scrollTo\(0, 0\);/, "QA İ-5: açık sayfaya yeniden tıklama başa sarar");
  assert.equal((sec.match(/window\.scrollTo\(/g) ?? []).length, 1, "O-2: sayfaSec'te yalnız aynı-sayfa dalında scrollTo");
  const c = oku("../../src/api/client.ts");
  assert.match(c, /const olumsuz = new Map<string, \{ hata: Error; zaman: number \}>\(\);\s*const OLUMSUZ_MS = 30_000;/, "O-3: olumsuz bellek 30 s");
  assert.match(c, /if \(olumsuzKayit && Date\.now\(\) - olumsuzKayit\.zaman < OLUMSUZ_MS\) return Promise\.reject\(olumsuzKayit\.hata\);/);
  assert.match(c, /if \(\(y\.status === 404 \|\| y\.status === 409 \|\| y\.status === 422\) && nesil === bellekNesli\) olumsuz\.set\(yol, \{ hata, zaman: Date\.now\(\) \}\);/, "O-3: yalnız «veri yok» kodları, eski uçuş yazmaz (QA İ-6)");
  assert.match(c, /function bellekBosalt\(\): void \{ bellekte\.clear\(\); olumsuz\.clear\(\); bellekNesli\+\+; \}/);
  assert.equal((c.match(/bellekte\.clear\(\)/g) ?? []).length, 1, "O-3: her yazma bellekBosalt ile iki belleği de boşaltır");
  assert.match(c, /for \(const \[k, v\] of bellekte\) bellekte\.set\(k, \{ veri: v\.veri, zaman: 0 \}\);\s*olumsuz\.clear\(\); bellekNesli\+\+;/, "O-3: damga eskitmesi olumsuz belleği de düşürür");
});

// ---------------------------------------------------------------- G3-A (UAT video Y-5 / U-2, 21.11): saatlik grafik seyrek seriye dayanıklı --------
test("G3-A: saatlik grafik sürekli ızgara (eksik saat null, veri uydurmaz), gün/doğuş etiketleri tutarlı, tikler gri", () => {
  const c = oku("../../src/features/sayfalar/ProductionForecastChart.tsx");
  assert.match(c, /const hamMs = forecast\.map\(\(p\) => toMs\(p\.ts\)\);\s*let adim = 3_600_000;/, "adım = serideki en küçük aralık, en çok 1 saat");
  assert.match(c, /const byMs = new Map\(forecast\.map\(\(p\) => \[toMs\(p\.ts\), p\]\)\);\s*let pts: \(ForecastPoint \| null\)\[\] = \[\];/);
  assert.match(c, /pts\.push\(byMs\.get\(t\) \?\? null\)/, "eksik saat null — istemci veri uydurmaz");
  assert.match(c, /cats = izgaraUyumlu \? pts\.map\(\(p, i\) => p \? p\.ts : new Date\(hamMs\[0\] \+ i \* adim\)\.toISOString\(\)\) : forecast\.map\(\(p\) => p\.ts\);/);
  assert.match(c, /const izgaraMakul = hamMs\.length > 0 && adim >= 60_000 && \(hamMs\[hamMs\.length - 1\] - hamMs\[0\]\) \/ adim <= 2000;\s*if \(izgaraMakul\) for/, "QA Ö-6: ms adımında döngüye girilmez");
  assert.match(c, /const izgaraUyumlu = izgaraMakul && pts\.filter\(Boolean\)\.length === forecast\.length && hamMs\.every\(\(v, i\) => i === 0 \|\| v > hamMs\[i - 1\]\);\s*if \(!izgaraUyumlu\) pts = forecast\.slice\(\);/, "QA İ-1/İ-2: sırasız/ızgara dışı seride eski davranış, nokta silinmez");
  for (const k of ["const loAdj = pts.map(", "const hiAdj = pts.map(", "pts.map((p) => (p ? (p.p25 as number) : null))", "splitPastFuture(pts.map((p) => (p ? p.p50 : null)), boundaryIdx)", "exceedIdx = pts.map(", "satureIdx = pts.map("])
    assert.ok(c.includes(k), `ızgara tabanlı seri: ${k}`);
  assert.doesNotMatch(c.slice(c.indexOf("if (!daily) {"), c.indexOf("} else {\n    // -------- daily envelope")), /forecast\.map\(\(p\) => p\.p50\)|forecast\.map\(\(p\) => \{\s*const lo = p\.p10/, "saatlik dalda forecast.map ile seri kalmadı");
  assert.match(c, /return cats\.length > 96 \? h === 0 : h % 6 === 0;/, "eksen aralığı ızgara uzunluğuna göre");
  assert.match(c, /itemStyle: \{ color: T\.mutedText \},   \/\/ G3-A \/ U-2/, "doğuş/batış tikleri amber değil");
  assert.doesNotMatch(c.slice(c.indexOf('name: "__gunes"'), c.indexOf('name: "__gunes"') + 900), /T\.actualLine/, "amber yalnız gerçekleşen");
});

// ---------------------------------------------------------------- G3-B (UAT video O-9/U-3/U-16/U-17/U-6, 21.11): renk sözleşmesi + eksen ölçeği ------
test("G3-B: amber yalnız gerçekleşen — dikkat rozeti uyarı ailesi, Mutabakat'ta tanımsız jeton yok, senaryo/hafta sonu/mevzuat nötr, 7g profili mavi", () => {
  const css = oku("../../src/index.css");
  assert.match(css, /\.rozet-dikkat \{ background: var\(--uyari-zemin\); color: var\(--uyari-metin\); \}/);
  assert.doesNotMatch(css, /\.rozet-dikkat \{ background: var\(--amber-zemin\)/);
  const m = oku("../../src/features/sayfalar/Mutabakat.tsx");
  assert.doesNotMatch(m, /amber-koyu|#8a5a00|ton=\{[^}]*"amber"/, "Mutabakat: tanımsız --amber-koyu ve ton=amber kalmadı");
  assert.equal((m.match(/\? "uyari" : undefined\}/g) ?? []).length, 2, "fark uyarıları ton=uyari");
  assert.match(oku("../../src/lib/durum.ts"), /senaryo: \{ etiket: "senaryo", sinif: "rozet-notr"/);
  const t = oku("../../src/features/sayfalar/Takvim.tsx");
  assert.match(t, /<span className="rozet rozet-notr rozet-kucuk" title=\{o\.not \?\? "Hafta sonuna denk geliyor/);
  assert.doesNotMatch(t, /o\.kaynak_turu === "mevzuat" \? "rozet-ok"/);
  assert.match(oku("../../src/features/santralim/Santralim.tsx"), /stroke="var\(--chart-p50-future\)"[^\n]*\n\s*strokeWidth=\{vurgu \? 2\.4 : 1\.4\}/, "U-3: profil tahmin mavisi");
  for (const f of ["../../src/features/sayfalar/Takvim.tsx", "../../src/features/sayfalar/FinansalEtki.tsx", "../../src/features/sayfalar/Portfoyler.tsx", "../../src/features/sayfalar/Hakkinda.tsx", "../../src/features/sayfalar/Digerleri.tsx", "../../src/features/sayfalar/Mutabakat.tsx", "../../src/features/sayfalar/Dogruluk.tsx"])
    assert.doesNotMatch(oku(f), /--amber-zemin|--amber-metin|--amber\b/, `amber jetonu durum için kullanılmaz: ${f}`);
  const d = oku("../../src/features/sayfalar/Digerleri.tsx");
  assert.match(d, /const enb = Math\.max\(1, Math\.max\(\.\.\.degerler\.map\(\(v\) => Math\.abs\(v \?\? 0\)\)\) \* 1\.2\);[\s\S]{0,300}const tepe = \(kat <= 1 \? 1 : kat <= 2 \? 2 : kat <= 5 \? 5 : 10\) \* us;/, "U-6: eksen ucu veriden");
  assert.doesNotMatch(d, /Math\.max\(100, Math\.ceil/);
  assert.match(d, /\$\{sayiTr\(x\.ort_hata_kw, tepe < 10 \? 1 : 0\)\} kW/, "QA İ-4: ipucu ondalığı eksenle aynı");
  // QA İ-6: Sayaç, Olay kaydı, kota rozeti, ölü rozet-amber; İ-1/İ-3
  for (const f of ["../../src/features/sayfalar/Sayac.tsx", "../../src/features/sayfalar/Olaylar.tsx"]) assert.doesNotMatch(oku(f), /var\(--amber|"amber"|\{amber\}/, `${f}: amber durum rengi değil`);
  assert.match(css, /\.plat-rozet-sari \{ background: var\(--uyari-zemin\); color: var\(--uyari-metin\); \}/);
  assert.match(css, /\.ayar-durum\.uyari \{ color: var\(--uyari-metin\); \}/);
  assert.doesNotMatch(oku("../../src/features/sayfalar/Dogruluk.tsx"), /rozet-amber/);
  for (const f of ["../../src/features/sayfalar/FinansalEtki.tsx", "../../src/features/sayfalar/Portfoyler.tsx"]) assert.match(oku(f), /eylem: "rozet-dikkat", oneri: "rozet-notr", bilgi: "rozet-notr"/, `${f}: eylem > öneri`);
  assert.doesNotMatch(oku("../../src/features/sayfalar/Mutabakat.tsx"), /\? "hata" : mesaj\.ton/, "QA İ-3: uyarı «hata» sınıfıyla basılmaz");
});

// ---------------------------------------------------------------- G3-C (UAT video O-13/O-11/U-12/U-19/U-20, 21.11): iç terimler, katlama, çipler ------
test("G3-C: Cipler bileşeni ve beş çok bilgili çip, Santralim katlamaları, müşteri yüzünde iç terim yok", () => {
  const p = oku("../../src/features/sayfalar/parcalar.tsx");
  assert.match(p, /export function Cipler\(\{ items, title \}: \{ items: \(string \| false \| null \| undefined\)\[\]; title\?: string \}\)/);
  assert.match(p, /<span className="dugme-sira kart-arac" title=\{title\}>\{liste\.map\(\(x, i\) => <span key=\{i\} className="cip">\{x\}<\/span>\)\}<\/span>/);
  for (const [f, n] of [["../../src/features/sayfalar/Mutabakat.tsx", 1], ["../../src/features/sayfalar/FinansalEtki.tsx", 2], ["../../src/features/sayfalar/Sayac.tsx", 1], ["../../src/features/sayfalar/Digerleri.tsx", 1]] as const)
    assert.equal((oku(f).match(/<Cipler items=\{/g) ?? []).length, n, `${f}: ${n} Cipler`);
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /<Katla ozet="Saatlik kıyas tablosu" not=\{`son \$\{sayiTr\(Math\.min\(24, golge\.saatler\.length\)\)\} saat; özet rozetleri yukarıda`\}>/);
  assert.match(s, /<Katla className="ayar-gelismis form-tam" ozet="YEK-G kaydı ve depolama ünitesi" not="nadiren değişen beyanlar">/);
  assert.match(s, /<Katla className="ayar-gelismis form-tam" ozet="İşletme ayarları" not="üretim programı sınırları, bakım pencereleri, tarife ve bütçe">/);
  assert.match(oku("../../src/index.css"), /\.ayar-izgara > \.katla \{ grid-column: 1 \/ -1; \}/);
  // U-19: Pilot kartı müşteri dilinde; sunucu notu ve kod şartı teknik notu yalnız ipucunda, saha beyan notu görünür
  assert.equal((s.match(/baslik="Sahaya bağlantı ön şartları ve saha toplayıcısı"/g) ?? []).length, 2);
  assert.doesNotMatch(s, /P0 kapı|P0 değil|>\{pilot\.not\}</, "P0 kapısı ve sunucu notu görünür yüzeyde yok");
  assert.match(s, /title=\{pilot\.not\}>Sahaya bağlantı, listedeki ön şartlar tamamlanmadan başlatılmaz\./);
  assert.match(s, /title=\{\[k\.aciklama, k\.kaynak === "saha" \? null : k\.not\]\.filter\(Boolean\)\.join\(" — "\)\}/);
  assert.match(s, /\{k\.kaynak === "saha" && k\.not \? ` · \$\{k\.not\}` : ""\}/, "QA İ-2: saha beyan notu görünür");
  // U-20
  assert.match(oku("../../src/features/sayfalar/Dogruluk.tsx"), /Kural sürümü: <span className="kimlik">\{gt\.kural_surumu \?\? "—"\}<\/span>/);
  const k = oku("../../src/features/sayfalar/Kurulus.tsx");
  for (const kap of ["veri_kalitesi:oku", "portfoy:oku", "finans:oku"]) assert.ok(k.includes(`"${kap}": `), `KAPSAM_AD ${kap}`);
  assert.match(k, /<div className="etiket-ust" style=\{\{ marginBottom: 2 \}\}>Webhook alıcıları<\/div>\s*<p className="soluk t-ikincil" style=\{\{ margin: "0 0 10px" \}\}>Olaylar: tahmin\.yeni ve alarm\.yeni\./);
  assert.doesNotMatch(s, /kapanması gereken kapılar|Pilot kapıları ya da|Pilot bilgisi bu kez/, "QA: Pilot kartı alt başlığı ve hata metni de müşteri dilinde");
  const d = oku("../../src/features/sayfalar/Digerleri.tsx");
  assert.doesNotMatch(d, /sunucu günlüğü/, "müşteri yüzünde «sunucu günlüğü» yok");
});

// ---------------------------------------------------------------- G4-A web parçası (UAT 21.11: Q-07, Q-23, Q-17, Q-13) ----------------------------------
test("G4-A web: kapsama satırı KPI ile aynı payda; boş kümede yanıltıcı metin yok", () => {
  const d = oku("../../src/features/sayfalar/Dogruluk.tsx");
  assert.match(d, /etiket: "Değerlendirilen gündüz saati", deger: `\$\{sayiTr\(b\.degerlendirilen_saat\)\} \/ \$\{sayiTr\(b\.gunduz_saat\)\}`, birim: "saat"/, "G4-5: 434/621 kalıbı");
  assert.match(d, /alt=\{b \? `ölçülen \$\{sayiTr\(b\.olcum\.olculdu_saat\)\} \/ \$\{sayiTr\(b\.olcum\.beklenen_saat\)\} saat \(gece dahil tüm saatler\); \$\{b\.olcum\.sinir_etiketi\}` : undefined\}/);
  assert.match(oku("../../src/features/sayfalar/Kgup.tsx"), /rv\.saatler\.length === 0\s*\? <p className="soluk t-ikincil"[^>]*>Bugün için kalan üretim saati yok;/, "G4-10/Q-23");
  assert.match(oku("../../src/features/sayfalar/Sayac.tsx"), /r\.saat_tahmini \? yuzde\(r\.olc_fark_pct\) : r\.saat_ortak \? <span className="soluk">aynı<\/span> : "—"/, "G4-10/Q-17");
  assert.match(oku("../../src/features/sayfalar/Portfoy.tsx"), /\$\{sayiTr\(\(p\?\.santraller \?\? \[\]\)\.filter\(\(r\) => r\.bugun_kwh == null \|\| r\.yarin_kwh == null\)\.length\)\} santralde tam gün tahmini yok; toplam gösterilmez/, "G4-10/Q-13");
});

test("G4-B web (K-A/K-B): bildirim muhatabı satırı, Plan dışı sözlükte, DSG kartı adlandırma + açıklama", () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /Bildirim muhatabı: \{seg\.bildirim\.muhatap_etiketi\} \(\{KESINLIK_AD\[seg\.bildirim\.kesinlik\] \?\? seg\.bildirim\.kesinlik\}\)/, "K-A Eksen 1 satırı");
  assert.match(s, /bildirim: d\.segment\.bildirim/, "ilk okuma bildirimi taşır");
  assert.match(s, /bildirim: r\.bildirim/, "Kaydet yanıtı bildirimi taşır");
  assert.equal((s.match(/setSeg\(\(s\) => \(s && r\.bildirim \? \{ \.\.\.s, bildirim: r\.bildirim \} : s\)\)/g) ?? []).length, 2, "QA Ö-3: DSG/katılımcı ve GTŞ Kaydet de satırı günceller");
  assert.match(s, /KESINLIK_AD: Record<string, string> = \{ dogrulandi: "doğrulandı", kismen: "kısmen doğrulandı", dogrulanamadi: "doğrulanamadı" \}/);
  assert.match(oku("../../src/lib/durum.ts"), /plan_disi: \{ etiket: "Plan dışı", sinif: "rozet-notr" \}/, "plan dışı nötr rozet — uyarı/alarm değil");
  assert.match(oku("../../src/api/types.ts"), /export interface BildirimBilgisi \{ muhatap: string; muhatap_etiketi: string; kesinlik: string; dayanak: string; not: string \}/);
  const p = oku("../../src/features/sayfalar/Portfoy.tsx");
  assert.match(p, /MWh \$\{dsg\.gosterge === false \? "grup payı \(eşik sonrası\)" : "net sapma"\}/, "K-B adlandırma");
  assert.match(p, /EDT ve KÜPST ayrı uzlaştırma kalemleridir, tek başına maliyetin toplamı değildir/, "K-B açıklama");
  assert.doesNotMatch(p, /MWh net sapma`\}/, "eski etiket hesap modunda kalmaz");
  const g = oku("../../src/features/genel/GenelBakis.tsx");
  assert.match(g, /MUTABAKAT_OZET\[r\.mutabakat_durum \?\? ""\] \?\? \(r\.mutabakat_durum === "saglikli" \? ", uzlaştırma belgeleri yüklü" : ""\)/, "«belgeler yüklü» yalnız sağlıklı boyutta (QA İ/Ö-14)");
  assert.match(g, /uygulanmiyor: "; uzlaştırma bildirimi bu santralde takip edilmiyor"/);
});

test("G4-C1 web: gerçekleşen seri API'den eşlenir (null sabiti yok), sentetik/arşiv notu, amber yalnız gerçekleşen", () => {
  const c = oku("../../src/api/client.ts");
  assert.match(c, /gercek_kw: s\.gercek_kw \?\? null \};/, "uyarla gercek_kw eşler");
  assert.doesNotMatch(c, /gercek_kw: null \};/, "eski null sabiti kalktı");
  assert.match(c, /gercek_kw\?: number \| null \}\[\];/, "ForecastYanit alanı");
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /grafikGercek\.length > 0 && veriTuru && veriTuru !== "canli" &&/, "sentetik/arşiv notu yalnız seri varken ve canlı değilken");
  assert.match(c, /gercek_veri_turu: g\.gercek_veri_turu \?\? null/, "QA Ö-1: veri türü seriyle gelir");
  assert.match(s, /simdiGercekSon\(seri\.saatlik, t0\)/, "QA İ-1: kadran son tamamlanmış saat");
  assert.match(s, /olcumMu \? `\$\{olcumAdi\} · \$\{olcumSaati\} saati` : "son tahminden"/, "QA İ-2: kadran etiketi veri türüne göre");
  assert.match(oku("../../src/features/sayfalar/Tahminler.tsx"), /seri\.gercek_veri_turu !== "canli" &&/, "QA Ö-2: Tahminler notu");
  assert.match(s, /actual=\{grafikGercek\}/, "grafik gerçekleşen girişi");
});

test("D-9 web: santral değişince ayar durumu sıfırlanır; yanıt gelmeden Kaydet yazmaz; eski yanıt yeni santrala yazılmaz", () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /useEffect\(\(\) => \{ setSeg\(null\); setSinif\(null\); setUevcb\(""\); setDsgKodu\(""\); setToplayici\(false\); setYekG\(false\); setDep\(null\);[\s\S]*?setLuyIstisna\(null\); setPozKaynak\(null\); setPozSabit\(""\);[^\n]*\}, \[plantId\]\);/, "sıfırlama efekti yalnız plantId'ye bağlı");
  for (const m of ["setDepMesaj", "setYekGMesaj", "setDsgMesaj"]) assert.match(s, new RegExp(`if \\(seg === null\\) \\{ ${m}\\(AYAR_OKUNMADI\\); return; \\}`), m);
  assert.equal((s.match(/if \(seg === null\) \{ setUevcbMesaj\(AYAR_OKUNMADI\); return; \}/g) ?? []).length, 2, "GTŞ adı ve UEVÇB Kaydet");
  assert.ok((s.match(/if \(plantRef\.current !== hedef\) return;/g) ?? []).length >= 5, "beş Kaydet yanıtı hedef santrala bağlı");
  assert.doesNotMatch(s, /if \(!seg\?\.segment\) \{ set\w+Mesaj\("Önce piyasa segmentini seçin\."\); return; \}/, "eski gevşek kapı kalmadı");
  // QA İ-1: GTŞ adı ve LÜY yükleyicileri satır yorumunun içinde kalmasın (v2.641 regresyonu): aynı fiziksel satırda setGtsAdi'den önce «//» yok
  const satir = s.split("\n").find((l) => l.includes("setGtsAdi(d.segment.gts_toplayici_adi"));
  assert.ok(satir, "yükleyici satırı var");
  const ciftEgik = satir!.indexOf("//"), gts = satir!.indexOf("setGtsAdi(d.segment.gts_toplayici_adi");
  assert.ok(ciftEgik === -1 || ciftEgik > gts, "setGtsAdi satır yorumu içinde değil");
  assert.match(s, /setUevcbArama\(""\); setUevcbAday\(null\); \}, \[plantId\]\);/, "QA Ö-5: UEVÇB aday listesi santralla düşer");
});

test("G4-C2 web: histogram ondalığı kutu genişliğinden, kutu genişliği eksende, etiket çakışması gizli", () => {
  const d = oku("../../src/features/sayfalar/Dogruluk.tsx");
  assert.match(d, /const kutuGen = hd\?\.kutu_mwh \?\? \(kutular\.length \? kutular\[0\]\.hi - kutular\[0\]\.lo : 1\);/);
  assert.match(d, /const ond = kutuGen >= 1 \? 0 : kutuGen >= 0\.1 \? 1 : 2;/, "0,01 MWh kutu → 2 hane");
  assert.match(d, /kutu \$\{sayiTr\(kutuGen, ond\)\} MWh`/, "kutu genişliği eksen adında (birim MWh)");
  assert.match(d, /axisLabel: \{ color: soluk, fontFamily: veri, fontSize: 13, hideOverlap: true \} \},   \/\/ G4-C2/);
  assert.match(oku("../../src/api/types.ts"), /kutu_mwh\?: number \| null; kutu_kaynak\?: string \| null;/);
});
