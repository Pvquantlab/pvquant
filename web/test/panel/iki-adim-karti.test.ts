/** Faz 0 §24 #2 (21.11.2026) — platform Hesabım: kurtarma kodu yönetim kartı bekçileri (kaynak pinleri).
 *  (1) A3 uçları yeniden kullanılır, yeni uç yok; (2) kodlar yalnız state'te: depolama/günlük yok, TekSeferlik notu; (3) rotasyon TOTP girdisiyle
 *  (prompt() yok), yeniden kurulumda parola + kod ve ardından çıkış; (4) kurtarma oturumunda rotasyon düğmesi çizilmez, uyarı var;
 *  (5) kalan sayı uçtan (ben.kalan_kurtarma), eşik ≤ 2 uyarı rozeti; (6) oturumYontemi jetonu depolamaz, imza iddiası yalnız ipucu;
 *  (7) satır içi // yorumu tek satır nesne literaline eklenmemiş (21.11 dersi). */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const oku = (p: string) => readFileSync(new URL(`../../src/${p}`, import.meta.url), "utf8");
const sayfalar = oku("features/yonetim/sayfalar.tsx");
const kart = sayfalar.slice(sayfalar.indexOf("function IkiAdimKarti("));
const yonetimTs = oku("api/yonetim.ts");

test("kart: A3 uçları yeniden kullanılır, yeni uç yok", () => {
  assert.match(kart, /yonetim\.ikiAdimKurtarmaYenile\(kod\)/);
  assert.match(kart, /yonetim\.ikiAdimYenidenKur\(kurtarmaOturumu \? \{\} : \{ sifre, kod \}\)/);
  assert.doesNotMatch(kart, /istek\(|fetch\(/);
  assert.match(yonetimTs, /ikiAdimKurtarmaYenile: \(kod: string\).*"\/iki-adim\/kurtarma-yenile"/);
  assert.match(yonetimTs, /ikiAdimYenidenKur: .*"\/iki-adim\/yeniden-kur"/);
});

test("kart: kodlar yalnız state'te — depolama, günlük, prompt yok; bir kez gösterim notu", () => {
  assert.doesNotMatch(kart, /localStorage|sessionStorage|indexedDB|console\./);
  assert.doesNotMatch(kart, /prompt\(/);
  assert.match(kart, /const \[kodlar, setKodlar\] = useState<string\[\] \| null>\(null\)/);
  assert.match(kart, /<TekSeferlik liste baslik="Yeni kurtarma kodlarınız" deger=\{kodlar\.join\("\\n"\)\}/);
  assert.match(kart, /denetim izine ve tarayıcı depolamasına yazılmaz/);
  assert.match(kart, /setKodlar\(null\); onBen\?\.\(\);/);                       // kapatınca bellekten silinir, kalan sayı uçtan yenilenir
});

test("kart: yeniden kimlik doğrulama — rotasyon TOTP girdisi, yeniden kurulum parola + kod, sonra çıkış", () => {
  assert.match(kart, /autoComplete="one-time-code" value=\{kod\}[\s\S]{0,80}required/);
  assert.match(kart, /type="password" autoComplete="current-password" value=\{sifre\}[\s\S]{0,80}required/);
  assert.match(kart, /await yonetim\.ikiAdimYenidenKur\([^)]*\); onCikis\?\.\(\); return;/);   // sunucu oturumları düşürür; arayüz çıkar
  assert.match(kart, /className="dugme dugme-tehlike" type="submit"/);
});

test("kart: kurtarma oturumunda rotasyon düğmesi yok, uyarı var; kalan sayı uçtan, eşik ≤ 2", () => {
  assert.match(kart, /const kurtarmaOturumu = oturumYontemi\(\) === "kurtarma";/);
  assert.match(kart, /\{!kurtarmaOturumu && <button className="dugme kucuk" onClick=\{\(\) => setKip\("yenile"\)\}>Kurtarma kodlarını yenile<\/button>\}/);
  assert.match(kart, /Bu oturumu kurtarma koduyla açtınız\./);
  assert.match(kart, /const kalan = ben\?\.kalan_kurtarma \?\? null;/);
  assert.match(kart, /kalan === 0 \? <span className="rozet rozet-uyari">kurtarma kodu kalmadı<\/span>/);
  assert.match(kart, /kalan <= 2 \? <span className="rozet rozet-uyari">\{kalan\} kurtarma kodu kaldı<\/span>/);
  assert.doesNotMatch(kart, /kalan_kurtarma\s*[-+]\s*1|\.length/);                      // arayüz saymaz
});

test("oturumYontemi: jeton yalnız okunur, depolanmaz; Yonetim kartı onBen/onCikis ile bağlar", () => {
  const f = yonetimTs.slice(yonetimTs.indexOf("export function oturumYontemi"));
  const govde = f.slice(0, f.indexOf("\n}\n") + 3);
  assert.match(govde, /atob\(p\.replace\(\/-\/g, "\+"\)\.replace\(\/_\/g, "\/"\)\)/);
  assert.doesNotMatch(govde, /setItem|console\./);
  assert.match(yonetimTs, /yalnız arayüz ipucu; yetki kararı sunucuda/);
  const yon = oku("features/yonetim/Yonetim.tsx");
  assert.match(yon, /<Hesap ben=\{ben\} onBen=\{\(\) => \{ yonetim\.ben\(\)\.then\(setBen\)\.catch\(\(\) => \{\}\); \}\} onCikis=\{cikis\} \/>/);
});

test("satır içi // yorumu tek satır nesne/arayüz literaline eklenmemiş (21.11 dersi; parti4 bekçisiyle aynı kuyruk deseni)", () => {
  for (const [ad, kaynak] of [["sayfalar.tsx (IkiAdimKarti)", kart], ["yonetim.ts", yonetimTs]] as const) {
    kaynak.split("\n").forEach((satir, i) => {
      const k = satir.indexOf("//"); if (k < 0 || satir.slice(0, k).includes("http")) return;
      const kuyruk = satir.slice(k + 2);
      assert.doesNotMatch(kuyruk, /\b[a-z_]+\??\s*:\s*(string|number|boolean|"[^"]*"|\{|\[|[a-zA-Z_]+\()/, `${ad}:${i + 1} satır içi yorum alan yutuyor: ${satir.trim().slice(0, 120)}`);
      assert.doesNotMatch(kuyruk, /\b(set[A-Z]\w*|on[A-Z]\w*)\s*\(/, `${ad}:${i + 1} satır içi yorum çağrı yutuyor: ${satir.trim().slice(0, 120)}`);
    });
  }
});
