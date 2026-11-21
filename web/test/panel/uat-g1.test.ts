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
  assert.match(c, /throw Object\.assign\(new Error\(`\$\{y\.status\} \$\{yol\}`\), \{ durum: y\.status, detay \}\);/, "getir: durum + detay");
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
