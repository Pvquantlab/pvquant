// v2.641 — Santralim denetimi Parti 3 (web pinleri): Türkçe sayı okuma (depolama, alarm eşikleri), YEK-G kutusu yalnız başarıda,
// fizik terimleri çoklu seçim, pilot/toplayıcı okunamadıysa kart gizlenmez, veri_gelmedi notu, «Diğer» sağlayıcı metni.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { sayiOku } from "../../src/lib/bicim.ts";
const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");

test("sayiOku: Türkçe binlik/ondalık", () => {
  assert.equal(sayiOku("12.000,5"), 12000.5);
  assert.equal(sayiOku("12,5"), 12.5);
  assert.equal(sayiOku("12.5"), 12.5);
  assert.equal(sayiOku("12.000"), 12000);
  assert.equal(sayiOku("1.234.567"), 1234567);
  assert.equal(sayiOku(" 7 "), 7);
  assert.equal(sayiOku("-0,25"), -0.25);
  assert.equal(sayiOku(""), null);
  assert.equal(sayiOku("abc"), null);
  assert.equal(sayiOku(null), null);
});

test("depolama ve alarm eşikleri sayiOku ile; YEK-G yalnız başarıda", () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /import \{ sayiOku as sayiOkuTr, tarihBicimi, yuzdeTr \} from "\.\.\/\.\.\/lib\/bicim";/);   // dosyadaki yerel tarife sayiOku ile çakışmasın
  assert.match(s, /depolama_gucu_mw: sayiOkuTr\(df\.guc\), depolama_kapasite_mwh: sayiOkuTr\(df\.kap\)/);
  assert.doesNotMatch(s, /Number\(df\.guc\.replace/);
  assert.match(s, /const v = sayiOkuTr\(ham\); if \(v === null\) \{ setAkMesaj\(`Geçersiz eşik: «\$\{a\.etiket\}» sayı olmalı/);
  // setYekG(v) yalnız then içinde
  assert.doesNotMatch(s, /\n    setYekG\(v\);\n    api\.segmentAyarla/);
  assert.match(s, /\.then\(\(\) => \{ setYekG\(v\); setYekGMesaj\(/);
});

test("fizik terimleri çoklu seçim, pilot hata kartı, metinler", () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /const aday: Record<string, string> = \{ \.\.\.ftSon, \[k\]: v \};/);
  assert.match(s, /const ftUygula = \(aday: Record<string, string>\) =>/);
  assert.doesNotMatch(s, /Object\.entries\(ftSon\)\[0\]/);
  assert.match(s, /onClick=\{\(\) => \{ if \(Object\.keys\(ftSon\)\.length > 0\) ftUygula\(ftSon\); \}\}>Uygula/);
  assert.match(s, /const \[pilotHata, setPilotHata\] = useState<string \| null>\(null\)/);
  assert.match(s, /\) : pilotHata \? \(\n\s+<Kart baslik="Sahaya bağlantı ön şartları ve saha toplayıcısı"/);   // G3-C (21.11): başlık müşteri dilinde
  assert.match(s, /hiç ölçüm gelmemiş santralda ve sanal test santralında bu alarm üretilmez/);
  assert.match(s, /Sağlayıcı adı \(yalnız santral ayarına ve denetim izine yazılır\)/);
  assert.doesNotMatch(s, /talep olarak not edilir/);
});
