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
