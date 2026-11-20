// v2.641 — Santralim denetimi Parti 2 (web pinleri): izleyici rolünde yazma alanları pasif, sessiz catch'ler mesaj veriyor,
// alarm kutusu taslak + tek Kaydet + deneme e-postası, PR kartında GHI uyarısı, bayat kirlenme rozetleri, LDYEÜM boşaltma/ondalık.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");

test("rol: dört yazma kartı fieldset ile pasifleşir, sessiz catch kalmadı", () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /const yazabilir = rolum\(\) !== "viewer";/);
  assert.equal((s.match(/<fieldset className="rol-alan" disabled=\{!yazabilir\}>/g) ?? []).length, 4);
  assert.equal((s.match(/<\/fieldset>/g) ?? []).length, 4);
  // veri çeken efektlerdeki catch(() => {}) kalır; yazma işlemlerinde kalmaz
  for (const yazma of ["api.pilotKapi(", "api.edgeToplayiciOlustur(", "api.edgeToplayiciIptal(", "api.bulutKimlikSil(", "api.segmentAyarla(plantId, e.target.value", "api.tarifeAyarla(plantId, null)"]) {
    const i = s.indexOf(yazma); assert.ok(i > 0, yazma);
    const par = s.slice(i, i + 420);
    assert.doesNotMatch(par, /\.catch\(\(\) => \{\}\)/, yazma);
  }
  assert.match(oku("../../src/index.css"), /\.rol-alan \{ border: 0; padding: 0; margin: 0; min-width: 0; \}/);
});

test("alarm: kutu taslağı, tek Kaydet, deneme e-postası", () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /const \[akSecili, setAkSecili\] = useState<string\[\]>\(\[\]\)/);
  assert.doesNotMatch(s, /api\.alarmKurallariAyarla\(plantId, k, ak\.esik\)/);
  assert.match(s, /api\.alarmKurallariAyarla\(plantId, akSecili, esik, alicilar\)/);
  assert.match(s, /checked=\{sabit \|\| akSecili\.includes\(k\)\}/);
  assert.match(s, /Kural seçimi değişti; kaydedilmedi\./);
  assert.match(s, /onClick=\{akDeneme\}[^>]*>Deneme e-postası gönder<\/button>/);
  assert.match(oku("../../src/api/client.ts"), /alarmDeneme: \(p: string\)[\s\S]*alarm-kurallari\/deneme`, "POST", \{\}\)/);
});

test("PR GHI uyarısı, bayat kirlenme rozetleri, LDYEÜM", () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /pr\.isinim_uyari && <span className="rozet rozet-kucuk rozet-uyari"/);
  assert.match(oku("../../src/api/types.ts"), /export interface PrKarti \{ isinim_uyari\?: string \| null;/);
  assert.match(s, /kir\.tazelik\?\.bayat \? "rozet-notr" :/);
  assert.match(s, /Son ölçüm tarihinde üretim kaybı olasıydı; bugünkü durum bilinmiyor\./);
  assert.match(s, /\{kir\.tazelik\?\.bayat \? " \(o tarihte\)" : ""\}/);
  assert.match(s, /const ld = ldyeum\.trim\(\) === "" \? 0 : Number/);
  assert.match(s, /String\(d\.segment\.lisans_yillik_uretim_mwh\)\.replace\("\.", ","\)/);
});
