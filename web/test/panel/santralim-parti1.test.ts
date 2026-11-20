// v2.640 — Santralim derin işlevsel denetimi (20.11.2026), Parti 1 (web pinleri).
// 1 İşletme ayarları formu sunucudan dolar (GET /eak) ve yalnız dokunulan alanı gönderir · 2 UEVÇB boş dize gönderilir (siler) ·
// 3 referans CSV saat sonu seçeneği + uyarılar görünür · 4 toplayıcı akışı ayrı durum kodu.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const oku = (yol: string) => readFileSync(new URL(yol, import.meta.url), "utf8");

test("client: GET /eak ve saat_sonu parametresi", () => {
  const cl = oku("../../src/api/client.ts");
  assert.match(cl, /eak: async \(p: string\): Promise<EakDurum \| null>/);
  assert.match(cl, /getir<EakDurum>\(`\/v1\/plants\/\$\{p\}\/eak`\)/);
  assert.match(cl, /pilot\/referans\?sinir=\$\{encodeURIComponent\(sinir\)\}&saat_sonu=\$\{saatSonu \? 1 : 0\}/);
  assert.match(oku("../../src/api/types.ts"), /export interface EakDurum \{/);
});

test("Santralim: işletme ayarları formu ön dolar, yalnız dokunulan alanlar gider, mesajda iç kod yok", () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /const eakYukle = \(\) => api\.eak\(plantId\)/);
  assert.match(s, /useEffect\(\(\) => \{ eakYukle\(\); \}, \[plantId, ds\]\)/);
  assert.match(s, /const eakDokunulan = useRef<Set<string>>\(new Set\(\)\)/);
  assert.match(s, /if \(Object\.keys\(g\)\.length === 0\) \{ setEakMesaj\("Değişiklik yok\."\); return; \}/);
  // eski toplu gönderim kalıbı yok: dengeleme_birimi her kaydette gitmiyor
  assert.doesNotMatch(s, /gecici_bitis: gecBitis \|\| null, dengeleme_birimi: dengelemeBirimi,/);
  // 15 form alanının her biri dokunulan kümesine bağlı
  const dokunmalar = s.match(/dokun\("(eak_kw|gecici|pozisyon|butce|prRef|kullSoz|sonTemizlik|temizlik|dengeleme_birimi|luy|dosyaSiklik|teminat|ariza)", /g) ?? [];
  assert.equal(dokunmalar.length, 15, dokunmalar.join(","));
  assert.match(s, /eakGucMetni\(r\.eak_bugun\.eak_mw\)/);
  assert.match(s, /eakKaynakEtiketi\(r\.eak_bugun\.kaynak\)/);
  assert.doesNotMatch(s, /MW \(\$\{r\.eak_bugun\.kaynak\}\)/);
});

test("Santralim: UEVÇB boş dize gönderilir; referans saat sonu + uyarılar; toplayıcı akışı ok", () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /api\.segmentAyarla\(plantId, seg\.segment, kod\.trim\(\)\)/);
  assert.doesNotMatch(s, /kod\.trim\(\) \|\| undefined/);
  assert.match(s, /api\.pilotReferans\(plantId, dosya, refSinirEtkin, refSaatSonu\)/);
  assert.match(s, /damga saat sonunu gösteriyor/);
  assert.match(s, /r\.uyarilar\.map\(\(u, i\) => <li key=\{i\}>\{u\}<\/li>\)/);
  assert.match(s, /vy\.baglanti_durumu\.kod === "veri_akisi_toplayici"/);
});

test("eak etiket ve güç metni", async () => {
  const s = oku("../../src/features/santralim/Santralim.tsx");
  assert.match(s, /kurulu_guc: "kurulu güç", ac_tavani: "AC sınırı", eak_alani: "EAK alanı", gecici: "geçici kısıt"/);
  assert.match(s, /mw >= 1 \? `\$\{sayiTr\(mw, 2\)\} MW` : `\$\{sayiTr\(Math\.round\(mw \* 1000\)\)\} kW`/);
});
